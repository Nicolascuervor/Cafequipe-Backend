import logging
import traceback

import httpx
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
import json

from .services import get_fallback_response, get_system_context, needs_system_data

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
                'Eres Syncra, el asistente virtual de Cafequipe, una empresa de gestión '
                'de inventario para la industria cafetera. Tu prioridad es ayudar con el '
                'sistema: inventario, bodegas, productos, reportes, usuarios y procesos '
                'internos. Además, puedes responder preguntas generales relacionadas con '
                'el café y la industria cafetera, como procesos de elaboración, tipos de '
                'café, terminología del sector o buenas prácticas, ya que son parte del '
                'contexto del negocio. Para preguntas completamente ajenas al sistema o '
                'al mundo del café (política, deportes, entretenimiento, etc.), indícalo '
                'amablemente y redirige al usuario hacia temas del sistema o del café. '
                'Responde siempre de forma clara, amable y sencilla. No inventes datos '
                'del sistema si no los conoces. IMPORTANTE: No uses asteriscos, negritas '
                'ni formato markdown. Responde en texto plano sin símbolos de formato.'
            )

            if needs_system_data(message):
                system_context = get_system_context()
                system_prompt += '\n\nDatos actuales del sistema:\n%s' % system_context
                logger.info("Incluyendo contexto del sistema: %s", system_context)

            messages = [{'role': 'system', 'content': system_prompt}]
            if history:
                messages.extend(history)
            messages.append({'role': 'user', 'content': message})

            stream_generator = self._call_openrouter(messages)
            logger.info("Iniciando streaming desde OpenRouter exitosamente")
            response = StreamingHttpResponse(stream_generator, content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        except _RateLimitError:
            logger.warning("Rate limit de OpenRouter — intentando fallback local")
            fallback = get_fallback_response(message)
            if fallback:
                chunk = json.dumps({"choices": [{"delta": {"content": fallback}}]})
                return StreamingHttpResponse([f"data: {chunk}\n\n"], content_type='text/event-stream')
            return Response(
                {'error': (
                    'El asistente está ocupado en este momento. '
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
            logger.warning("Error del servicio OpenRouter: %s — intentando fallback local", e)
            fallback = get_fallback_response(message)
            if fallback:
                chunk = json.dumps({"choices": [{"delta": {"content": fallback}}]})
                return StreamingHttpResponse([f"data: {chunk}\n\n"], content_type='text/event-stream')
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

    def _call_openrouter(self, messages):
        headers = {
            'Authorization': 'Bearer %s' % settings.OPENROUTER_API_KEY,
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:8000',
            'X-Title': 'Cafequipe',
        }
        payload = {
            'model': settings.OPENROUTER_MODEL,
            'messages': messages,
            'stream': True,
        }

        logger.info("Enviando petición a OpenRouter con modelo %s (Streaming)", settings.OPENROUTER_MODEL)

        try:
            client = httpx.Client(timeout=60.0)
            request = client.build_request(
                'POST',
                '%s/chat/completions' % settings.OPENROUTER_BASE_URL,
                headers=headers,
                json=payload
            )
            response = client.send(request, stream=True)

            if response.status_code == 429:
                response.close()
                client.close()
                logger.error("Rate limit")
                raise _RateLimitError()
            if response.status_code in (401, 403):
                response.close()
                client.close()
                raise _AuthError()
            if response.status_code == 402:
                response.close()
                client.close()
                raise _ServiceError('Créditos insuficientes en OpenRouter.')
            if response.status_code == 404:
                response.close()
                client.close()
                raise _ServiceError('El modelo configurado no está disponible en OpenRouter.')
            if response.status_code >= 500:
                response.close()
                client.close()
                raise _ServiceError(
                    'Error del servidor OpenRouter (%s).' % response.status_code
                )

            response.raise_for_status()
            
            def stream_generator():
                try:
                    for line in response.iter_lines():
                        if line:
                            yield f"{line}\n\n"
                finally:
                    response.close()
                    client.close()

            return stream_generator()

        except httpx.ConnectError as exc:
            raise _ServiceError(
                'No se pudo conectar con el servicio del asistente.'
            ) from exc
        except httpx.TimeoutException as exc:
            raise _ServiceError(
                'El asistente tardó demasiado en responder. Intenta de nuevo.'
            ) from exc
        except (_RateLimitError, _AuthError, _ServiceError):
            raise
        except Exception as exc:
            raise _ServiceError('Error inesperado: %s' % str(exc)) from exc
