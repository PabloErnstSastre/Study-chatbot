"""
╔══════════════════════════════════════════════════════════════╗
║           🎓 StudyBot - Asistente de Estudio con IA          ║
║                    Powered by Google Gemini                   ║
╚══════════════════════════════════════════════════════════════╝

Script principal del chatbot de ayuda al estudio.
Gestiona el perfil del estudiante, genera horarios y responde
preguntas organizativas usando un LLM.
"""

import os
import json
import sys
import re
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────
#  Dependencias con instalación automática
# ──────────────────────────────────────────────
def _install(pkg: str):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    import google.generativeai as genai
except ImportError:
    print("📦 Instalando google-generativeai...")
    _install("google-generativeai")
    import google.generativeai as genai

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich.columns import Columns
    from rich import box
    from rich.rule import Rule
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    from rich.style import Style
    from rich.align import Align
except ImportError:
    print("📦 Instalando rich...")
    _install("rich")
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich.columns import Columns
    from rich import box
    from rich.rule import Rule
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    from rich.style import Style
    from rich.align import Align

# ──────────────────────────────────────────────
#  Configuración de colores y consola
# ──────────────────────────────────────────────
console = Console()

PALETTE = {
    "primary":   "#7C3AED",   # violeta
    "secondary": "#06B6D4",   # cyan
    "accent":    "#F59E0B",   # ámbar
    "success":   "#10B981",   # verde
    "danger":    "#EF4444",   # rojo
    "muted":     "#6B7280",   # gris
    "bot":       "#A78BFA",   # lila suave
    "user":      "#34D399",   # verde menta
    "bg":        "#1E1B4B",   # azul oscuro
}

# ──────────────────────────────────────────────
#  Archivo de perfil del estudiante
# ──────────────────────────────────────────────
PROFILE_FILE = Path("student_profile.json")

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


# ══════════════════════════════════════════════
#  Modelo de datos del estudiante
# ══════════════════════════════════════════════
class StudentProfile:
    """Almacena y gestiona los datos del estudiante."""

    def __init__(self):
        self.nombre: str = ""
        self.asignaturas: list[dict] = []
        # horas disponibles por día (0-24)
        self.horas_por_dia: dict[str, float] = {d: 0.0 for d in DIAS}
        self.priorizar_ocio: bool = False
        self.nivel: str = ""  # bachillerato / universidad / oposiciones / etc.

    # ─── Serialización ───────────────────────
    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "nivel": self.nivel,
            "asignaturas": self.asignaturas,
            "horas_por_dia": self.horas_por_dia,
            "priorizar_ocio": self.priorizar_ocio,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StudentProfile":
        p = cls()
        p.nombre = data.get("nombre", "")
        p.nivel = data.get("nivel", "")
        p.asignaturas = data.get("asignaturas", [])
        p.horas_por_dia = data.get("horas_por_dia", {d: 0.0 for d in DIAS})
        p.priorizar_ocio = data.get("priorizar_ocio", False)
        return p

    # ─── Persistencia ────────────────────────
    def save(self):
        PROFILE_FILE.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def load() -> "StudentProfile | None":
        if PROFILE_FILE.exists():
            data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
            return StudentProfile.from_dict(data)
        return None

    # ─── Resumen compacto ─────────────────────
    def summary_text(self) -> str:
        asig_lines = "\n".join(
            f"  • {a['nombre']} (importancia: {a['importancia']}/5, "
            f"dificultad: {a['dificultad']}/5, créditos: {a.get('creditos', 'N/A')})"
            for a in self.asignaturas
        )
        horas_lines = "\n".join(
            f"  • {d}: {self.horas_por_dia.get(d, 0):.1f}h"
            for d in DIAS
        )
        ocio = "Sí (minimizar fines de semana)" if self.priorizar_ocio else "No"
        return (
            f"PERFIL DEL ESTUDIANTE:\n"
            f"  Nombre: {self.nombre}\n"
            f"  Nivel: {self.nivel}\n"
            f"  Priorizar ocio en fin de semana: {ocio}\n\n"
            f"ASIGNATURAS:\n{asig_lines}\n\n"
            f"HORAS DISPONIBLES:\n{horas_lines}"
        )

    @property
    def total_horas_semana(self) -> float:
        return sum(self.horas_por_dia.values())

    @property
    def total_horas_semana_laboral(self) -> float:
        return sum(self.horas_por_dia[d] for d in DIAS[:5])

    @property
    def total_horas_fin_de_semana(self) -> float:
        return sum(self.horas_por_dia[d] for d in DIAS[5:])


# ══════════════════════════════════════════════
#  Interfaz de configuración del perfil
# ══════════════════════════════════════════════
class ProfileSetup:
    """Guía al usuario para crear o editar su perfil."""

    def __init__(self, profile: StudentProfile | None = None):
        self.profile = profile or StudentProfile()

    def run(self) -> StudentProfile:
        console.print()
        console.print(
            Panel(
                "[bold #7C3AED]Configuración del Perfil de Estudiante[/]\n"
                "[#6B7280]Responde las siguientes preguntas para personalizar tu asistente[/]",
                border_style="#7C3AED",
                padding=(1, 4),
            )
        )

        self._ask_personal()
        self._ask_asignaturas()
        self._ask_horas()
        self._ask_ocio()
        self.profile.save()
        return self.profile

    # ─── Datos personales ─────────────────────
    def _ask_personal(self):
        console.print(Rule("[#06B6D4]Datos personales[/]", style="#06B6D4"))
        self.profile.nombre = Prompt.ask(
            "  [#34D399]Tu nombre[/]",
            default=self.profile.nombre or "Estudiante",
        )
        self.profile.nivel = Prompt.ask(
            "  [#34D399]Nivel de estudios[/] [#6B7280](ej: bachillerato, universidad, oposiciones)[/]",
            default=self.profile.nivel or "universidad",
        )

    # ─── Asignaturas ──────────────────────────
    def _ask_asignaturas(self):
        console.print()
        console.print(Rule("[#06B6D4]Asignaturas[/]", style="#06B6D4"))
        console.print(
            "  [#6B7280]Añade tus asignaturas con su importancia (1-5) y dificultad (1-5).[/]\n"
            "  [#6B7280]Escribe [bold]FIN[/bold] cuando hayas terminado.[/]"
        )

        if self.profile.asignaturas:
            console.print(
                f"  [#F59E0B]Tienes {len(self.profile.asignaturas)} asignatura(s) guardadas. "
                "¿Quieres reemplazarlas?[/]"
            )
            if not Confirm.ask("  Reemplazar asignaturas existentes", default=False):
                return

        self.profile.asignaturas = []
        i = 1
        while True:
            console.print(f"\n  [bold #A78BFA]Asignatura {i}[/]")
            nombre = Prompt.ask("    Nombre").strip()
            if nombre.upper() == "FIN" or not nombre:
                break

            importancia = self._ask_int(
                "    Importancia (1=baja … 5=muy alta)", 1, 5, default=3
            )
            dificultad = self._ask_int(
                "    Dificultad (1=fácil … 5=muy difícil)", 1, 5, default=3
            )
            creditos_str = Prompt.ask(
                "    Créditos / ponderación [#6B7280](Enter para omitir)[/]",
                default="",
            )
            creditos = float(creditos_str) if creditos_str else None

            self.profile.asignaturas.append(
                {
                    "nombre": nombre,
                    "importancia": importancia,
                    "dificultad": dificultad,
                    "creditos": creditos,
                }
            )
            i += 1

        if not self.profile.asignaturas:
            console.print("  [#EF4444]Debes añadir al menos una asignatura.[/]")
            return self._ask_asignaturas()

    # ─── Horas disponibles ────────────────────
    def _ask_horas(self):
        console.print()
        console.print(Rule("[#06B6D4]Disponibilidad semanal[/]", style="#06B6D4"))
        console.print("  [#6B7280]Indica cuántas horas puedes dedicar al estudio cada día.[/]")

        for dia in DIAS:
            current = self.profile.horas_por_dia.get(dia, 0)
            h = self._ask_float(
                f"    {dia}", 0.0, 16.0, default=current
            )
            self.profile.horas_por_dia[dia] = h

    # ─── Ocio en fin de semana ────────────────
    def _ask_ocio(self):
        console.print()
        console.print(Rule("[#06B6D4]Preferencias de ocio[/]", style="#06B6D4"))
        self.profile.priorizar_ocio = Confirm.ask(
            "  ¿Quieres [bold]reducir al mínimo[/bold] el estudio en fin de semana "
            "para compaginar con el ocio?",
            default=self.profile.priorizar_ocio,
        )

    # ─── Helpers ──────────────────────────────
    @staticmethod
    def _ask_int(prompt: str, min_v: int, max_v: int, default: int) -> int:
        while True:
            raw = Prompt.ask(f"{prompt} [#6B7280][{default}][/]", default=str(default))
            try:
                v = int(raw)
                if min_v <= v <= max_v:
                    return v
            except ValueError:
                pass
            console.print(f"    [#EF4444]Introduce un número entre {min_v} y {max_v}.[/]")

    @staticmethod
    def _ask_float(prompt: str, min_v: float, max_v: float, default: float) -> float:
        while True:
            raw = Prompt.ask(f"{prompt} [#6B7280](horas) [{default}][/]", default=str(default))
            try:
                v = float(raw.replace(",", "."))
                if min_v <= v <= max_v:
                    return v
            except ValueError:
                pass
            console.print(f"    [#EF4444]Introduce un número entre {min_v} y {max_v}.[/]")


# ══════════════════════════════════════════════
#  Motor del chatbot (Gemini)
# ══════════════════════════════════════════════
class StudyBot:
    """Chatbot de estudio usando Google Gemini con memoria de conversación."""

    MODEL_NAME = "gemini-2.0-flash"

    SYSTEM_PROMPT_TEMPLATE = """
Eres StudyBot, un asistente de estudio inteligente, empático y motivador.
Tu especialidad es ayudar a los estudiantes a organizar su tiempo de estudio
de manera eficiente y equilibrada.

{perfil}

════════════════════════════
REGLAS DE COMPORTAMIENTO:
════════════════════════════

1. DISTRIBUCIÓN DE HORAS:
   - Calcula siempre las horas de estudio semanales disponibles del estudiante.
   - Reparte las horas entre asignaturas según su importancia Y dificultad.
   - Fórmula base de peso:  peso = importancia × 0.6 + dificultad × 0.4
   - Si el estudiante quiere priorizar el ocio: las horas de Sábado y Domingo
     deben reducirse al mínimo posible (idealmente 0 o máximo 1h/día de repaso ligero),
     compensando con más horas entre semana.
   - Respeta siempre las horas máximas disponibles por día que indicó el estudiante.

2. FORMATO DE HORARIOS:
   - Cuando generes un horario semanal, usa una tabla con columnas: Día | Asignatura(s) | Horas.
   - Muestra siempre el total de horas semanales por asignatura en un resumen.

3. PERSONALIZACIÓN:
   - Llama al estudiante por su nombre: {nombre}.
   - Adapta el tono al nivel de estudios: {nivel}.
   - Sé motivador pero realista.

4. CONSEJOS:
   - Incluye técnicas de estudio relevantes cuando sea apropiado
     (Pomodoro, mapas mentales, etc.).
   - Sugiere descansos adecuados (ej: 5-10 min por cada 45-50 min de estudio).

5. RESTRICCIONES:
   - No inventes asignaturas ni horas que el estudiante no haya indicado.
   - Si la pregunta no es de estudio/organización, responde brevemente y
     redirige la conversación al tema educativo.
   - Responde siempre en español, con formato Markdown claro y bien estructurado.

6. CASOS ESPECIALES:
   - Si el estudiante tiene exámenes próximos, ajusta el plan intensificando
     la asignatura correspondiente.
   - Si pide "plan de choque" o "urgente", concentra la mayoría de horas en
     las 2-3 asignaturas más importantes/difíciles.
"""

    def __init__(self, api_key: str, profile: StudentProfile):
        genai.configure(api_key=api_key)
        self.profile = profile
        self.system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
            perfil=profile.summary_text(),
            nombre=profile.nombre,
            nivel=profile.nivel,
        )
        self.model = genai.GenerativeModel(
            model_name=self.MODEL_NAME,
            system_instruction=self.system_prompt,
        )
        self.chat = self.model.start_chat(history=[])
        self.history: list[dict] = []

    def send(self, user_message: str) -> str:
        """Envía un mensaje al modelo y devuelve la respuesta."""
        response = self.chat.send_message(user_message)
        return response.text

    def reset_chat(self):
        """Reinicia el historial de conversación manteniendo el perfil."""
        self.chat = self.model.start_chat(history=[])
        self.history = []


# ══════════════════════════════════════════════
#  Interfaz de Chat
# ══════════════════════════════════════════════
class ChatUI:
    """Gestiona la interfaz de usuario del chat en terminal."""

    COMMANDS = {
        "/perfil":   "Ver o editar tu perfil de estudiante",
        "/horario":  "Pedir un horario semanal optimizado",
        "/resumen":  "Ver resumen de tus asignaturas y horas",
        "/reset":    "Reiniciar la conversación (mantiene el perfil)",
        "/ayuda":    "Mostrar esta ayuda",
        "/salir":    "Salir del chatbot",
    }

    def __init__(self, bot: StudyBot, profile: StudentProfile):
        self.bot = bot
        self.profile = profile

    # ─── Loop principal ───────────────────────
    def run(self):
        self._print_welcome()
        # Mensaje de bienvenida automático del bot
        self._bot_intro()

        while True:
            try:
                user_input = self._get_user_input()
            except (KeyboardInterrupt, EOFError):
                self._goodbye()
                break

            if not user_input:
                continue

            # Comandos especiales
            if user_input.startswith("/"):
                should_exit = self._handle_command(user_input.strip().lower())
                if should_exit:
                    break
                continue

            # Respuesta del bot
            self._send_and_display(user_input)

    # ─── Bienvenida ───────────────────────────
    def _print_welcome(self):
        console.clear()
        banner = """
[bold #7C3AED]  ╔══════════════════════════════════════════════╗
  ║   🎓  StudyBot — Tu Asistente de Estudio IA  ║
  ╚══════════════════════════════════════════════╝[/]"""
        console.print(banner)
        console.print(
            f"  [#6B7280]Powered by Google Gemini · Estudiante: "
            f"[bold #34D399]{self.profile.nombre}[/] · "
            f"[bold #06B6D4]{self.profile.nivel}[/][/]"
        )
        console.print(
            "  [#6B7280]Escribe [bold #F59E0B]/ayuda[/] para ver los comandos disponibles.[/]\n"
        )
        console.print(Rule(style="#3730A3"))

    def _bot_intro(self):
        intro_msg = (
            f"generar un mensaje de bienvenida personalizado breve para {self.profile.nombre}, "
            f"estudiante de {self.profile.nivel} con {len(self.profile.asignaturas)} asignaturas. "
            "Menciona que estás listo para ayudarle a organizar su estudio. Sé cálido y motivador."
        )
        with self._spinner("StudyBot está pensando..."):
            response = self.bot.send(intro_msg)
        self._print_bot_message(response)

    # ─── Input del usuario ────────────────────
    def _get_user_input(self) -> str:
        console.print()
        text = Text()
        text.append("  Tú › ", style=f"bold {PALETTE['user']}")
        console.print(text, end="")
        return input().strip()

    # ─── Enviar y mostrar respuesta ───────────
    def _send_and_display(self, user_input: str):
        self._print_user_message(user_input)
        with self._spinner("StudyBot está pensando..."):
            try:
                response = self.bot.send(user_input)
            except Exception as e:
                response = f"⚠️ Error al contactar con la IA: {e}"
        self._print_bot_message(response)

    # ─── Comandos ─────────────────────────────
    def _handle_command(self, cmd: str) -> bool:
        """Devuelve True si hay que salir."""
        if cmd == "/salir":
            self._goodbye()
            return True

        elif cmd == "/ayuda":
            self._print_help()

        elif cmd == "/perfil":
            self._edit_profile()

        elif cmd == "/resumen":
            self._print_profile_summary()

        elif cmd == "/horario":
            self._request_schedule()

        elif cmd == "/reset":
            self.bot.reset_chat()
            console.print(
                Panel(
                    "✅ Conversación reiniciada. El perfil se mantiene.",
                    border_style=PALETTE["success"],
                    padding=(0, 2),
                )
            )
        else:
            console.print(
                f"  [#EF4444]Comando desconocido:[/] {cmd}  "
                f"[#6B7280](escribe /ayuda)[/]"
            )
        return False

    # ─── Editar perfil ────────────────────────
    def _edit_profile(self):
        console.print(
            Panel(
                "Vamos a actualizar tu perfil. Los cambios se guardarán automáticamente.",
                border_style=PALETTE["accent"],
                padding=(0, 2),
            )
        )
        setup = ProfileSetup(self.profile)
        self.profile = setup.run()
        # Recrear el bot con el perfil actualizado
        self.bot.profile = self.profile
        self.bot.system_prompt = StudyBot.SYSTEM_PROMPT_TEMPLATE.format(
            perfil=self.profile.summary_text(),
            nombre=self.profile.nombre,
            nivel=self.profile.nivel,
        )
        self.bot.reset_chat()
        console.print(
            Panel(
                "✅ Perfil actualizado y conversación reiniciada.",
                border_style=PALETTE["success"],
                padding=(0, 2),
            )
        )

    # ─── Resumen del perfil ───────────────────
    def _print_profile_summary(self):
        # Tabla de asignaturas
        table_asig = Table(
            title=f"📚 Asignaturas de {self.profile.nombre}",
            box=box.ROUNDED,
            border_style=PALETTE["primary"],
            header_style=f"bold {PALETTE['secondary']}",
            show_lines=True,
        )
        table_asig.add_column("Asignatura", style="bold white")
        table_asig.add_column("Importancia", justify="center")
        table_asig.add_column("Dificultad", justify="center")
        table_asig.add_column("Créditos", justify="center", style=PALETTE["muted"])

        for a in self.profile.asignaturas:
            imp_bar = "★" * a["importancia"] + "☆" * (5 - a["importancia"])
            dif_bar = "▮" * a["dificultad"] + "▯" * (5 - a["dificultad"])
            table_asig.add_row(
                a["nombre"],
                f"[{PALETTE['accent']}]{imp_bar}[/]",
                f"[{PALETTE['danger']}]{dif_bar}[/]",
                str(a["creditos"]) if a["creditos"] else "—",
            )

        # Tabla de horas
        table_horas = Table(
            title="⏰ Horas disponibles",
            box=box.ROUNDED,
            border_style=PALETTE["secondary"],
            header_style=f"bold {PALETTE['primary']}",
        )
        table_horas.add_column("Día", style="bold")
        table_horas.add_column("Horas", justify="right")
        table_horas.add_column("", justify="left")

        for dia in DIAS:
            h = self.profile.horas_por_dia.get(dia, 0)
            is_weekend = dia in ("Sábado", "Domingo")
            color = PALETTE["accent"] if is_weekend else PALETTE["success"]
            bar = "█" * int(h) + ("▌" if h % 1 >= 0.5 else "")
            table_horas.add_row(
                f"[{color}]{dia}[/]",
                f"[bold]{h:.1f}h[/]",
                f"[{color}]{bar}[/]",
            )

        table_horas.add_section()
        table_horas.add_row(
            "[bold]TOTAL SEMANA[/]",
            f"[bold #A78BFA]{self.profile.total_horas_semana:.1f}h[/]",
            "",
        )

        console.print()
        console.print(table_asig)
        console.print()
        console.print(table_horas)
        ocio_txt = (
            "[bold #10B981]✔ Sí[/] — fin de semana libre"
            if self.profile.priorizar_ocio
            else "[bold #EF4444]✘ No[/] — estudio también el fin de semana"
        )
        console.print(f"\n  Priorizar ocio: {ocio_txt}\n")

    # ─── Solicitar horario ────────────────────
    def _request_schedule(self):
        prompt = (
            "Genera un horario de estudio semanal detallado y optimizado para mí, "
            "teniendo en cuenta todas mis asignaturas, su importancia, dificultad, "
            "mis horas disponibles cada día y mis preferencias de ocio en fin de semana. "
            "Incluye una tabla semanal por día y un resumen de horas por asignatura al final. "
            "Añade también 2-3 consejos de productividad específicos para mi situación."
        )
        self._print_user_message("[Solicitud automática de horario]")
        with self._spinner("Generando tu horario personalizado..."):
            try:
                response = self.bot.send(prompt)
            except Exception as e:
                response = f"⚠️ Error: {e}"
        self._print_bot_message(response)

    # ─── Ayuda ────────────────────────────────
    def _print_help(self):
        table = Table(
            title="📖 Comandos disponibles",
            box=box.ROUNDED,
            border_style=PALETTE["primary"],
            header_style=f"bold {PALETTE['secondary']}",
        )
        table.add_column("Comando", style=f"bold {PALETTE['accent']}")
        table.add_column("Descripción", style="white")
        for cmd, desc in self.COMMANDS.items():
            table.add_row(cmd, desc)
        console.print()
        console.print(table)

    # ─── Mensajes visuales ────────────────────
    def _print_user_message(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        console.print(
            Panel(
                text,
                title=f"[bold {PALETTE['user']}]🧑 {self.profile.nombre}[/]  "
                      f"[{PALETTE['muted']}]{ts}[/]",
                title_align="right",
                border_style=PALETTE["user"],
                padding=(0, 2),
            )
        )

    def _print_bot_message(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        try:
            rendered = Markdown(text)
        except Exception:
            rendered = text  # fallback si el markdown falla
        console.print(
            Panel(
                rendered,
                title=f"[bold {PALETTE['bot']}]🎓 StudyBot[/]  "
                      f"[{PALETTE['muted']}]{ts}[/]",
                title_align="left",
                border_style=PALETTE["bot"],
                padding=(1, 2),
            )
        )

    # ─── Spinner ──────────────────────────────
    @staticmethod
    def _spinner(msg: str):
        return Progress(
            SpinnerColumn(spinner_name="dots", style=PALETTE["primary"]),
            TextColumn(f"[{PALETTE['muted']}]{msg}[/]"),
            transient=True,
            console=console,
        )

    def _goodbye(self):
        console.print()
        console.print(
            Panel(
                f"[bold {PALETTE['primary']}]¡Hasta pronto, {self.profile.nombre}! 🎓[/]\n"
                "[#6B7280]Recuerda: la constancia es la clave del éxito.[/]",
                border_style=PALETTE["primary"],
                padding=(1, 4),
            )
        )


# ══════════════════════════════════════════════
#  Punto de entrada
# ══════════════════════════════════════════════
def get_api_key() -> str:
    """Obtiene la API key de Gemini desde env var o la pide al usuario."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key

    # Intentar cargar desde .env
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key

    console.print()
    console.print(
        Panel(
            "[bold #F59E0B]🔑 Se necesita una API Key de Google Gemini[/]\n\n"
            "Puedes obtenerla gratis en:\n"
            "[link=https://aistudio.google.com/app/apikey]"
            "https://aistudio.google.com/app/apikey[/link]\n\n"
            "También puedes guardarla en un archivo [bold].env[/] en este directorio:\n"
            "  [#6B7280]GEMINI_API_KEY=tu_clave_aqui[/]\n"
            "O como variable de entorno [bold]GEMINI_API_KEY[/].",
            border_style="#F59E0B",
            padding=(1, 4),
        )
    )
    key = Prompt.ask("  Introduce tu API Key ahora", password=True)
    # Guardar para la próxima vez
    if Confirm.ask("  ¿Guardar la API Key en el archivo .env para futuras sesiones?", default=True):
        env_file.write_text(f'GEMINI_API_KEY="{key}"\n', encoding="utf-8")
        console.print(f"  [#10B981]✔ Clave guardada en {env_file.absolute()}[/]")
    return key


def main():
    # 1. Obtener API key
    api_key = get_api_key()

    console.print()
    console.print(
        Panel(
            "[bold #7C3AED]🎓 StudyBot — Asistente de Estudio con IA[/]\n"
            "[#6B7280]Bienvenido al asistente de organización de estudio[/]",
            border_style="#7C3AED",
            padding=(1, 4),
        )
    )

    # 2. Cargar o crear perfil
    existing_profile = StudentProfile.load()
    if existing_profile and existing_profile.nombre:
        console.print(
            f"\n  [#10B981]✔ Perfil encontrado:[/] [bold]{existing_profile.nombre}[/] "
            f"({existing_profile.nivel})"
        )
        use_existing = Confirm.ask(
            "  ¿Usar este perfil existente?", default=True
        )
        if use_existing:
            profile = existing_profile
        else:
            profile = ProfileSetup().run()
    else:
        console.print("\n  [#F59E0B]No se encontró ningún perfil guardado. Vamos a crearlo.[/]")
        profile = ProfileSetup().run()

    if not profile.asignaturas:
        console.print(
            "[#EF4444]Error: el perfil no tiene asignaturas. Configura el perfil primero.[/]"
        )
        sys.exit(1)

    # 3. Iniciar el bot
    console.print(f"\n  [#6B7280]Conectando con Gemini ({StudyBot.MODEL_NAME})...[/]")
    try:
        bot = StudyBot(api_key=api_key, profile=profile)
    except Exception as e:
        console.print(f"\n  [#EF4444]Error al inicializar el modelo: {e}[/]")
        sys.exit(1)

    # 4. Lanzar interfaz de chat
    ui = ChatUI(bot=bot, profile=profile)
    ui.run()


if __name__ == "__main__":
    main()
