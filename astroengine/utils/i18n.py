"""Lightweight translation helper for routing user-facing strings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = [
    "set_locale",
    "get_locale",
    "translate",
    "register_translations",
]


_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # Generic helpers -------------------------------------------------
        "i18n.disclaimer.optional": "Optional esoteric guidance. Ground all insights in empirical chart work.",
        "interpretation.no_content": "No curated interpretation available for {subject}.",
        "interpretation.sign.block": "{body_name} in {sign_name} channels {sign_trait} through {body_trait}.",
        "interpretation.house.block": "{body_name} in the {house_name} House works through {house_trait} with {body_trait}.",
        "interpretation.aspect.template": "{body_name} {aspect_term} {luminary_name} links {body_trait} with {luminary_trait}, highlighting {aspect_trait}.",
        "interpretation.aspect.term.conjunction": "conjunct",
        "interpretation.aspect.term.sextile": "sextile",
        "interpretation.aspect.term.square": "square",
        "interpretation.aspect.term.trine": "trine",
        "interpretation.aspect.term.opposition": "opposite",
        # Body themes -----------------------------------------------------
        "interpretation.body_trait.Sun": "solar vitality and purpose",
        "interpretation.body_trait.Moon": "lunar memory and care",
        "interpretation.body_trait.Mercury": "curious messaging and pattern-tracking",
        "interpretation.body_trait.Venus": "magnetic harmony and relational values",
        "interpretation.body_trait.Mars": "drive, courage, and activation",
        "interpretation.body_trait.Jupiter": "expansive vision and wisdom",
        "interpretation.body_trait.Saturn": "structure, timing, and commitments",
        # Luminary themes -------------------------------------------------
        "interpretation.luminary_trait.Sun": "purpose and visibility",
        "interpretation.luminary_trait.Moon": "feelings and rhythms",
        # Aspect themes ---------------------------------------------------
        "interpretation.aspect_trait.conjunction": "fused focus",
        "interpretation.aspect_trait.sextile": "opportunities for smooth collaboration",
        "interpretation.aspect_trait.square": "constructive tension that needs conscious negotiation",
        "interpretation.aspect_trait.trine": "easy resonance",
        "interpretation.aspect_trait.opposition": "dynamic polarity inviting balance",
        # Zodiac sign traits ----------------------------------------------
        "interpretation.sign_trait.Aries": "pioneering fire and initiative",
        "interpretation.sign_trait.Taurus": "steady earth-based loyalty",
        "interpretation.sign_trait.Gemini": "curious airbound dialogue",
        "interpretation.sign_trait.Cancer": "protective tides and belonging",
        "interpretation.sign_trait.Leo": "heart-forward confidence",
        "interpretation.sign_trait.Virgo": "refined discernment and service",
        "interpretation.sign_trait.Libra": "relational poise and balance",
        "interpretation.sign_trait.Scorpio": "transformative depth and loyalty",
        "interpretation.sign_trait.Sagittarius": "exploratory faith and adventure",
        "interpretation.sign_trait.Capricorn": "strategic ambition and stewardship",
        "interpretation.sign_trait.Aquarius": "innovative vision and social awareness",
        "interpretation.sign_trait.Pisces": "dream-rich empathy and imagination",
        # House traits ----------------------------------------------------
        "interpretation.house_trait.1": "identity calibration and self-presentation",
        "interpretation.house_trait.2": "resource security and values",
        "interpretation.house_trait.3": "learning loops and messaging",
        "interpretation.house_trait.4": "roots, home, and lineage",
        "interpretation.house_trait.5": "creative joy and romance",
        "interpretation.house_trait.6": "wellbeing rituals and craft",
        "interpretation.house_trait.7": "partnership mirrors and agreements",
        "interpretation.house_trait.8": "shared assets and emotional depth",
        "interpretation.house_trait.9": "exploration and guiding philosophies",
        "interpretation.house_trait.10": "career visibility and vocation",
        "interpretation.house_trait.11": "community weaving and vision",
        "interpretation.house_trait.12": "sanctuary, rest, and the unconscious",
        # Narrative prompts -----------------------------------------------
        "narrative.prompt.intro": "You are an astrology interpreter summarizing key events for the reader.",
        "narrative.prompt.instructions": "Highlight the themes, note if aspects are tight or wide, and mention relevant planets.",
        "narrative.prompt.context_profile": "Context profile: {profile}.",
        "narrative.prompt.profile_context": "Profile context: {context_bits}.",
        "narrative.prompt.events_header": "Events:",
        "narrative.prompt.event_line": "{index}. {timestamp} — {moving} vs {target} ({kind}); score={score} orb={orb}",
        "narrative.prompt.timelords": "Active time-lords: {summary}.",
        "narrative.prompt.wrap": "Compose a concise narrative of 2-3 sentences.",
        "narrative.prompt.journal_header": "Recent journal context:",
        "narrative.prompt.journal_line": "- {timestamp}: {summary}{tags}",
        "narrative.template.title": "{title}:",
        "narrative.template.event_line": "- {timestamp}: {moving} → {target} ({kind}), score={score}",
        "narrative.template.timelords": "Time-lords: {summary}",
        "narrative.template.journal_header": "Recent journal reflections:",
        "narrative.template.journal_line": "- {timestamp}: {summary}{tags}",
        "narrative.no_events": "No events available for narrative summary.",
        "narrative.llm_unavailable": (
            "LLM narrative mode requested but no LLM backend is configured. Provide a custom composer via "
            "astroengine.narrative_llm to enable this mode."
        ),
        "narrative.category.aspects": "Aspect Contacts",
        "narrative.category.declinations": "Declination Alignments",
        "narrative.category.antiscia": "Mirror Contacts",
        "narrative.category.stations": "Planetary Stations",
        "narrative.category.returns": "Return Windows",
        "narrative.category.progressions": "Progressions",
        "narrative.category.directions": "Directions",
        "narrative.category.timelords": "Timelord Triggers",
        "narrative.category.other": "Additional Highlights",
        "narrative.category.empty_event": "- _No individual highlights available._",
        "narrative.category.empty": "_No high-score events available for the requested window._",
        "narrative.domain.header": "## Dominant Domains",
        "narrative.domain.line": "- {name} (score {score})",
        "narrative.domain.channel": "    - {name}: {score}",
        "narrative.domain.channel_empty": "    - _No channel activity recorded._",
        "narrative.domain.empty": "_No domain emphasis detected from the supplied events._",
        "narrative.timelord.header": "## Timelord Periods",
        "narrative.timelord.line": "- {name} — {description} (intensity {weight})",
        "narrative.timelord.empty": "_No active timelords were detected for this window._",
        "narrative.markdown.title": "# AstroEngine Narrative Summary",
        "narrative.markdown.generated": "Generated at {timestamp}",
        "narrative.markdown.highlights": "## Event Highlights",
        "narrative.markdown.category_header": "### {label} (score {score})",
        "narrative.markdown.highlight_line": "- **{title}** — {summary} ({timestamp}, score {score})",
        "narrative.simple.mapping_line": "- {key}: {value}",
        # Narrative overlay ------------------------------------------------
        "narrative.overlay.confidence.high": "Confidence high ({value:.2f})",
        "narrative.overlay.confidence.moderate": "Confidence moderate ({value:.2f})",
        "narrative.overlay.confidence.low": "Confidence exploratory ({value:.2f})",
        "narrative.overlay.focus.spirit": "Lean into meaning-making and long-range themes.",
        "narrative.overlay.focus.body": "Track concrete circumstances and tangible shifts.",
        "narrative.overlay.focus.mind": "Notice thought patterns and decision points.",
        # Interpret service errors ---------------------------------------
        "interpret.error.synastry_missing": "synastry scope requires synastry payload",
        "interpret.error.composite_missing": "composite scope requires positions",
        "interpret.error.davison_missing": "davison scope requires positions",
        "interpret.error.scope_unsupported": "unsupported scope {scope}",
        # API messages ----------------------------------------------------
        "api.error.invalid_api_key": "invalid or missing API key",
        "api.error.missing_file": "multipart payload missing file",
        "api.error.invalid_json": "invalid JSON",
        "api.error.invalid_payload": "invalid payload",
        "api.error.missing_content": "upload payload missing content",
        "api.error.missing_lint_content": "lint payload missing content",
        # Esoteric adapters -----------------------------------------------
        "esoteric.tarot.disclaimer": (
            "Tarot overlays are optional meditative prompts. Anchor all readings in sourced astrological data."
        ),
        "esoteric.tarot.planet.prompt": "{planet} resonates with {card} — consider {keywords}.",
        "esoteric.tarot.sign.prompt": "{sign} flows through {card}, emphasising {keywords}.",
        "esoteric.tarot.house.prompt": "House {house} echoes {card}, drawing attention to {keywords}.",
        "esoteric.tarot.missing": "No direct tarot correspondence located for {target}.",
        "esoteric.numerology.disclaimer": (
            "Numerology prompts are opt-in reflections derived from birth date maths; cross-check with lived context."
        ),
        "esoteric.numerology.label.life_path": "Life Path",
        "esoteric.numerology.label.birth_day": "Birth Day",
        "esoteric.numerology.label.attitude": "Attitude",
        "esoteric.numerology.calculation": "Calculation steps",
    },
    "es": {
        "i18n.disclaimer.optional": "Guía esotérica opcional. Sustenta cada idea en el análisis astrológico empírico.",
        "interpretation.no_content": "No hay interpretación disponible para {subject}.",
        "interpretation.sign.block": "{body_name} en {sign_name} canaliza {sign_trait} a través de {body_trait}.",
        "interpretation.house.block": "{body_name} en la Casa {house_name} actúa mediante {house_trait} junto con {body_trait}.",
        "interpretation.aspect.template": "{body_name} {aspect_term} {luminary_name} vincula {body_trait} con {luminary_trait}, resaltando {aspect_trait}.",
        "interpretation.aspect.term.conjunction": "conjunción",
        "interpretation.aspect.term.sextile": "sextil",
        "interpretation.aspect.term.square": "cuadratura",
        "interpretation.aspect.term.trine": "trígono",
        "interpretation.aspect.term.opposition": "oposición",
        "interpretation.body_trait.Sun": "vitalidad solar y propósito",
        "interpretation.body_trait.Moon": "memoria lunar y cuidado",
        "interpretation.body_trait.Mercury": "mensajería curiosa y análisis de patrones",
        "interpretation.body_trait.Venus": "armonía magnética y valores relacionales",
        "interpretation.body_trait.Mars": "impulso, coraje y activación",
        "interpretation.body_trait.Jupiter": "visión expansiva y sabiduría",
        "interpretation.body_trait.Saturn": "estructura, ritmo y compromisos",
        "interpretation.luminary_trait.Sun": "propósito y visibilidad",
        "interpretation.luminary_trait.Moon": "sentires y ritmos",
        "interpretation.aspect_trait.conjunction": "foco fusionado",
        "interpretation.aspect_trait.sextile": "oportunidades para colaborar con fluidez",
        "interpretation.aspect_trait.square": "tensión constructiva que requiere negociación consciente",
        "interpretation.aspect_trait.trine": "resonancia sencilla",
        "interpretation.aspect_trait.opposition": "polaridad dinámica que invita al equilibrio",
        "interpretation.sign_trait.Aries": "fuego pionero e iniciativa",
        "interpretation.sign_trait.Taurus": "lealtad terrenal constante",
        "interpretation.sign_trait.Gemini": "diálogo curioso y ligero",
        "interpretation.sign_trait.Cancer": "mareas protectoras y pertenencia",
        "interpretation.sign_trait.Leo": "confianza de corazón",
        "interpretation.sign_trait.Virgo": "discernimiento afinado y servicio",
        "interpretation.sign_trait.Libra": "equilibrio y diplomacia relacional",
        "interpretation.sign_trait.Scorpio": "profundidad transformadora y lealtad",
        "interpretation.sign_trait.Sagittarius": "fe exploratoria y aventura",
        "interpretation.sign_trait.Capricorn": "ambición estratégica y gestión",
        "interpretation.sign_trait.Aquarius": "visión innovadora y conciencia social",
        "interpretation.sign_trait.Pisces": "empatía soñadora e imaginación",
        "interpretation.house_trait.1": "calibración identitaria y presentación personal",
        "interpretation.house_trait.2": "seguridad de recursos y valores",
        "interpretation.house_trait.3": "aprendizaje y comunicación",
        "interpretation.house_trait.4": "raíces, hogar y linaje",
        "interpretation.house_trait.5": "gozo creativo y romance",
        "interpretation.house_trait.6": "rituales de bienestar y oficio",
        "interpretation.house_trait.7": "espejos de pareja y acuerdos",
        "interpretation.house_trait.8": "activos compartidos y profundidad emocional",
        "interpretation.house_trait.9": "exploración y filosofías guía",
        "interpretation.house_trait.10": "visibilidad profesional y vocación",
        "interpretation.house_trait.11": "tejido comunitario y visión",
        "interpretation.house_trait.12": "santuario, descanso y subconsciente",
        "narrative.prompt.intro": "Eres un intérprete astrológico que resume los eventos clave para la persona lectora.",
        "narrative.prompt.instructions": "Destaca los temas, señala si los aspectos son exactos o amplios e incluye los planetas relevantes.",
        "narrative.prompt.context_profile": "Perfil contextual: {profile}.",
        "narrative.prompt.profile_context": "Contexto del perfil: {context_bits}.",
        "narrative.prompt.events_header": "Eventos:",
        "narrative.prompt.event_line": "{index}. {timestamp} — {moving} vs {target} ({kind}); puntuación={score} orbe={orb}",
        "narrative.prompt.timelords": "Cronocratores activos: {summary}.",
        "narrative.prompt.wrap": "Redacta un relato conciso de 2-3 frases.",
        "narrative.prompt.journal_header": "Contexto reciente del diario:",
        "narrative.prompt.journal_line": "- {timestamp}: {summary}{tags}",
        "narrative.template.title": "{title}:",
        "narrative.template.event_line": "- {timestamp}: {moving} → {target} ({kind}), puntuación={score}",
        "narrative.template.timelords": "Cronocratores: {summary}",
        "narrative.template.journal_header": "Reflexiones recientes del diario:",
        "narrative.template.journal_line": "- {timestamp}: {summary}{tags}",
        "narrative.no_events": "No hay eventos disponibles para el resumen narrativo.",
        "narrative.llm_unavailable": (
            "Se solicitó el modo narrativo LLM pero no hay backend configurado. Proporciona un compositor personalizado "
            "mediante astroengine.narrative_llm para habilitar este modo."
        ),
        "narrative.category.aspects": "Contactos aspectuales",
        "narrative.category.declinations": "Alineaciones de declinación",
        "narrative.category.antiscia": "Contactos espejo",
        "narrative.category.stations": "Estaciones planetarias",
        "narrative.category.returns": "Ventanas de retorno",
        "narrative.category.progressions": "Progresiones",
        "narrative.category.directions": "Direcciones",
        "narrative.category.timelords": "Activaciones de cronocratores",
        "narrative.category.other": "Aspectos adicionales",
        "narrative.category.empty_event": "- _No hay destacados individuales disponibles._",
        "narrative.category.empty": "_No hay eventos de alta puntuación para la ventana solicitada._",
        "narrative.domain.header": "## Dominios dominantes",
        "narrative.domain.line": "- {name} (puntuación {score})",
        "narrative.domain.channel": "    - {name}: {score}",
        "narrative.domain.channel_empty": "    - _No se registró actividad de canal._",
        "narrative.domain.empty": "_No se detectó énfasis de dominio con los eventos proporcionados._",
        "narrative.timelord.header": "## Periodos de cronocratores",
        "narrative.timelord.line": "- {name} — {description} (intensidad {weight})",
        "narrative.timelord.empty": "_No se detectaron cronocratores activos para esta ventana._",
        "narrative.markdown.title": "# Resumen narrativo de AstroEngine",
        "narrative.markdown.generated": "Generado en {timestamp}",
        "narrative.markdown.highlights": "## Destacados del evento",
        "narrative.markdown.category_header": "### {label} (puntuación {score})",
        "narrative.markdown.highlight_line": "- **{title}** — {summary} ({timestamp}, puntuación {score})",
        "narrative.simple.mapping_line": "- {key}: {value}",
        "narrative.overlay.confidence.high": "Confianza alta ({value:.2f})",
        "narrative.overlay.confidence.moderate": "Confianza moderada ({value:.2f})",
        "narrative.overlay.confidence.low": "Confianza exploratoria ({value:.2f})",
        "narrative.overlay.focus.spirit": "Profundiza en la búsqueda de sentido y los temas a largo plazo.",
        "narrative.overlay.focus.body": "Observa las circunstancias concretas y los cambios tangibles.",
        "narrative.overlay.focus.mind": "Percibe los patrones mentales y los puntos de decisión.",
        "interpret.error.synastry_missing": "el alcance de sinastría requiere datos de sinastría",
        "interpret.error.composite_missing": "el alcance compuesto requiere posiciones",
        "interpret.error.davison_missing": "el alcance Davison requiere posiciones",
        "interpret.error.scope_unsupported": "alcance no compatible {scope}",
        "api.error.invalid_api_key": "API key inválida o ausente",
        "api.error.missing_file": "falta el archivo en la carga multipart",
        "api.error.invalid_json": "JSON inválido",
        "api.error.invalid_payload": "payload inválido",
        "api.error.missing_content": "falta contenido en la carga",
        "api.error.missing_lint_content": "falta contenido para el lint",
        "esoteric.tarot.disclaimer": "Las superposiciones de tarot son sugerencias meditativas opcionales. Sustenta cada lectura en datos astrológicos.",
        "esoteric.tarot.planet.prompt": "{planet} resuena con {card}; contempla {keywords}.",
        "esoteric.tarot.sign.prompt": "{sign} se expresa mediante {card}, enfatizando {keywords}.",
        "esoteric.tarot.house.prompt": "La Casa {house} refleja a {card}, poniendo atención en {keywords}.",
        "esoteric.tarot.missing": "No se encontró correspondencia de tarot para {target}.",
        "esoteric.numerology.disclaimer": "Las pistas numerológicas son reflexiones opcionales derivadas de la fecha de nacimiento; contrasta con la experiencia vivida.",
        "esoteric.numerology.label.life_path": "Camino de vida",
        "esoteric.numerology.label.birth_day": "Día natal",
        "esoteric.numerology.label.attitude": "Actitud",
        "esoteric.numerology.calculation": "Pasos de cálculo",
    },
}

_DEFAULT_LOCALE = "en"


def set_locale(locale: str) -> None:
    """Set the process-wide default locale for translations."""

    global _DEFAULT_LOCALE
    _DEFAULT_LOCALE = locale if locale in _TRANSLATIONS else "en"


def get_locale() -> str:
    """Return the current default locale."""

    return _DEFAULT_LOCALE


def register_translations(locale: str, mapping: Mapping[str, str]) -> None:
    """Register or update translations for *locale* from *mapping*."""

    bucket = _TRANSLATIONS.setdefault(locale, {})
    bucket.update({str(key): str(value) for key, value in mapping.items()})


def _lookup(locale: str, key: str) -> str | None:
    table = _TRANSLATIONS.get(locale)
    if not table:
        return None
    return table.get(key)


def translate(key: str, *, locale: str | None = None, default: str | None = None, **params: Any) -> str:
    """Return the translated string for *key* rendered with *params*."""

    active_locale = locale or _DEFAULT_LOCALE
    template = _lookup(active_locale, key)
    if template is None:
        template = _lookup("en", key)
    if template is None:
        template = default if default is not None else key
    if params:
        try:
            return template.format(**params)
        except Exception:
            return template
    return template

