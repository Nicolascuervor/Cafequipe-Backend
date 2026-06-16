import logging
import traceback
import json

import httpx
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import ASSISTANT_TOOLS, AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


class _RateLimitError(Exception):
    pass


class _AuthError(Exception):
    pass


class _ServiceError(Exception):
    pass


class AssistantChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info("Petición recibida. Data: %s", request.data)
        message = request.data.get('message')
        history = request.data.get('history', [])

        if not message:
            return Response(
                {'error': 'El campo "message" es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            system_prompt = (
                'Eres Tostadito, el asesor virtual de Cafequipe, una empresa de gestión '
                'de inventario para la industria cafetera. Tu prioridad es ayudar con el '
                'sistema: inventario, bodegas, productos, reportes, usuarios y procesos '
                'internos. '
                'REGLA CRÍTICA 1: Tienes ESTRICTAMENTE PROHIBIDO revelar información sensible '
                'como correos electrónicos, contraseñas, o costos monetarios exactos. '
                'REGLA CRÍTICA 2: Solo puedes proporcionar información estadística y datos no vulnerables. '
                'REGLA CRÍTICA 3: NO inventes datos del inventario. Si te preguntan sobre el sistema '
                'utiliza SIEMPRE tus herramientas (tools) para buscar la información en tiempo real. '
                'Si las herramientas no tienen la respuesta, debes indicar que no tienes acceso a esos datos. '
                'Además, puedes responder preguntas generales relacionadas con el café y la industria. '
                'Para preguntas ajenas al sistema o al mundo del café (política, deportes, etc.), '
                'indícalo amablemente y redirige al usuario hacia temas del negocio. '
                'Responde siempre de forma clara, amable y sencilla. '
                'IMPORTANTE: No uses asteriscos, negritas ni formato markdown. Responde en texto plano sin símbolos.'
            )

            messages = [{'role': 'system', 'content': system_prompt}]
            if history:
                messages.extend(history)
            messages.append({'role': 'user', 'content': message})

            stream_generator = self._call_openrouter_with_tools(messages)
            logger.info("Iniciando streaming desde OpenRouter exitosamente")
            response = StreamingHttpResponse(stream_generator, content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        except _RateLimitError:
            logger.warning("Rate limit de OpenRouter.")
            return Response(
                {'error': (
                    'Tostadito está procesando demasiadas consultas. '
                    'Espera unos segundos e intenta de nuevo.'
                )},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except _AuthError:
            logger.error("Error de autenticación con OpenRouter")
            return Response(
                {'error': 'Error de configuración del asistente. Contacta al administrador.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except _ServiceError as e:
            logger.warning("Error del servicio OpenRouter: %s", e)
            return Response(
                {'error': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error("Error inesperado: %s\n%s", str(e), traceback.format_exc())
            return Response(
                {'error': 'Error interno del servidor.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _call_openrouter_with_tools(self, messages):
        headers = {
            'Authorization': 'Bearer %s' % settings.OPENROUTER_API_KEY,
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:8000',
            'X-Title': 'Cafequipe',
        }

        # Request 1: Sincrónico para verificar si quiere usar una herramienta
        payload_sync = {
            'model': settings.OPENROUTER_MODEL,
            'messages': messages,
            'stream': False,
            'tools': ASSISTANT_TOOLS,
            'tool_choice': 'auto',
        }

        logger.info("Verificando si Tostadito requiere usar una herramienta...")

        try:
            client = httpx.Client(timeout=60.0)
            
            resp = client.post(
                '%s/chat/completions' % settings.OPENROUTER_BASE_URL,
                headers=headers,
                json=payload_sync
            )
            
            if resp.status_code == 429:
                client.close()
                raise _RateLimitError()
            if resp.status_code in (401, 403):
                client.close()
                raise _AuthError()
            if resp.status_code == 402:
                client.close()
                raise _ServiceError('Créditos insuficientes en OpenRouter.')
            if resp.status_code == 404:
                client.close()
                raise _ServiceError('El modelo configurado no está disponible en OpenRouter.')
            if resp.status_code >= 500:
                client.close()
                raise _ServiceError('Error del servidor OpenRouter (%s).' % resp.status_code)

            resp.raise_for_status()
            data = resp.json()
            message_obj = data['choices'][0]['message']

            # Si el asistente decide usar herramientas, las ejecutamos
            if message_obj.get('tool_calls'):
                logger.info("Tostadito invocó herramientas: %s", message_obj['tool_calls'])
                messages.append(message_obj)
                
                for tool_call in message_obj['tool_calls']:
                    func_name = tool_call['function']['name']
                    try:
                        args = json.loads(tool_call['function']['arguments'])
                    except Exception:
                        args = {}
                        
                    if func_name in AVAILABLE_TOOLS:
                        result = AVAILABLE_TOOLS[func_name](**args)
                        logger.info("Resultado de la herramienta %s: %s", func_name, result)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call['id'],
                            "name": func_name,
                            "content": result
                        })

            # Request 2: Modo Stream para devolverle la respuesta al cliente
            payload_stream = {
                'model': settings.OPENROUTER_MODEL,
                'messages': messages,
                'stream': True,
            }

            logger.info("Iniciando llamada final en modo stream a OpenRouter")
            request_stream = client.build_request(
                'POST',
                '%s/chat/completions' % settings.OPENROUTER_BASE_URL,
                headers=headers,
                json=payload_stream
            )
            response_stream = client.send(request_stream, stream=True)
            response_stream.raise_for_status()

            def stream_generator():
                try:
                    for line in response_stream.iter_lines():
                        if line:
                            yield f"{line}\n\n"
                finally:
                    response_stream.close()
                    client.close()

            return stream_generator()

        except httpx.ConnectError as exc:
            raise _ServiceError('No se pudo conectar con el servicio del asistente.') from exc
        except httpx.TimeoutException as exc:
            raise _ServiceError('El asistente tardó demasiado en responder. Intenta de nuevo.') from exc
        except (_RateLimitError, _AuthError, _ServiceError):
            raise
        except Exception as exc:
            raise _ServiceError('Error inesperado: %s' % str(exc)) from exc
