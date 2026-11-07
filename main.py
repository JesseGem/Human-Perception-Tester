import csv
import random
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


CSV_FIELDS = [
    "participant_id",
    "date_time",
    "visual_condition",
    "task_type",
    "response",
    "target_distance",
    "target_size",
    "time_taken_seconds",
    "ease_of_use",
]


class HumanPerceptionTester(tk.Tk):
    """Main window for the Human Perception & Performance Tester."""

    def __init__(self):
        super().__init__()

        self.title("Human Perception & Performance Tester")
        self.geometry("1120x760")
        self.minsize(940, 680)

        self.base_dir = Path(__file__).resolve().parent
        self.results_dir = self.base_dir / "results"
        self.results_file = self.results_dir / "experiment_results.csv"
        self.prepare_results_file()

        # These are the visual settings currently applied to the application.
        self.settings = {
            "contrast": "Medium",
            "size": "Medium",
            "brightness": 100,
        }

        self.contrast_var = tk.StringVar(self, value=self.settings["contrast"])
        self.size_var = tk.StringVar(self, value=self.settings["size"])
        self.brightness_var = tk.IntVar(self, value=self.settings["brightness"])

        # Identification-task state is stored on the application so the
        # participant ID can remain available when navigating between pages.
        self.participant_id_var = tk.StringVar(self, value="")
        self.identification_response_var = tk.StringVar(self, value="")
        self.identification_rating_var = tk.IntVar(self, value=0)
        self.identification_start_time = None
        self.identification_trial_active = False
        self.identification_canvas = None
        self.identification_status = None
        self.identification_response_entry = None
        self.identification_submit_button = None
        self.identification_start_button = None
        self.identification_rating_buttons = []

        # Target-hitting (Fitts' Law) experiment state.
        # Each of the four size/distance combinations is repeated three times.
        self.fitts_participant_entry = None
        self.fitts_canvas = None
        self.fitts_status_label = None
        self.fitts_trial_label = None
        self.fitts_rating_var = tk.IntVar(self, value=0)
        self.fitts_rating_buttons = []
        self.fitts_save_button = None
        self.fitts_session_button = None
        self.fitts_conditions = []
        self.fitts_trial_index = 0
        self.fitts_stage = "idle"  # idle, ready, active, awaiting_rating, complete
        self.fitts_started_at = None
        self.fitts_elapsed = None
        self.fitts_pending_result = None
        self.fitts_misses = 0
        self.fitts_start_x = 90
        self.fitts_start_y = 150
        self.fitts_target_x = None
        self.fitts_target_y = None
        self.fitts_target_diameter = None
        self.fitts_status_message = "Enter a participant ID and start a session."

        self.current_page = "Overview"
        self.nav_buttons = {}
        self.preview_widgets = {}

        self.rebuild_application()

    # ---------------------------------------------------------
    # CSV FILE PREPARATION AND DATA LOGGING
    # ---------------------------------------------------------

    def prepare_results_file(self):
        """Create the results directory and CSV header if they do not exist."""
        self.results_dir.mkdir(parents=True, exist_ok=True)
        if not self.results_file.exists():
            with self.results_file.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
                writer.writeheader()

    def save_result(self, result):
        """Append one experiment result to the CSV file."""
        self.prepare_results_file()
        with self.results_file.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
            writer.writerow(result)

    def count_saved_results(self):
        """Return the number of experiment records currently in the CSV file."""
        self.prepare_results_file()
        with self.results_file.open("r", newline="", encoding="utf-8") as file:
            return max(0, sum(1 for _ in csv.DictReader(file)))

    # ---------------------------------------------------------
    # VISUAL THEME
    # ---------------------------------------------------------

    @staticmethod
    def dim_colour(hex_colour, brightness):
        """Reduce a colour's luminance to simulate screen brightness."""
        hex_colour = hex_colour.lstrip("#")
        factor = max(0.20, min(1.0, brightness / 100))
        red = int(int(hex_colour[0:2], 16) * factor)
        green = int(int(hex_colour[2:4], 16) * factor)
        blue = int(int(hex_colour[4:6], 16) * factor)
        return f"#{red:02x}{green:02x}{blue:02x}"

    def get_theme(self, contrast=None, brightness=None):
        """Return the colour palette for the selected visual conditions."""
        contrast = contrast or self.settings["contrast"]
        brightness = brightness if brightness is not None else self.settings["brightness"]

        palettes = {
            "High": {
                "window": "#F7F9FC",
                "surface": "#FFFFFF",
                "text": "#101828",
                "muted": "#344054",
                "border": "#667085",
                "primary": "#174EA6",
                "primary_text": "#FFFFFF",
                "sidebar": "#101828",
                "sidebar_text": "#FFFFFF",
                "sidebar_muted": "#D0D5DD",
                "sidebar_active": "#315CA8",
                "success": "#087443",
                "danger": "#B42318",
            },
            "Medium": {
                "window": "#F2F4F7",
                "surface": "#FFFFFF",
                "text": "#344054",
                "muted": "#667085",
                "border": "#D0D5DD",
                "primary": "#356AE6",
                "primary_text": "#FFFFFF",
                "sidebar": "#24364B",
                "sidebar_text": "#F9FAFB",
                "sidebar_muted": "#C7D0DC",
                "sidebar_active": "#405D7C",
                "success": "#16865B",
                "danger": "#B42318",
            },
            "Low": {
                "window": "#DADDE1",
                "surface": "#D3D6DA",
                "text": "#858B93",
                "muted": "#989EA6",
                "border": "#B8BDC4",
                "primary": "#A4ADB8",
                "primary_text": "#626A73",
                "sidebar": "#777E86",
                "sidebar_text": "#BFC4CB",
                "sidebar_muted": "#A5ABB3",
                "sidebar_active": "#9299A1",
                "success": "#8C9690",
                "danger": "#989EA6",
            },
        }

        selected = palettes.get(contrast, palettes["Medium"])
        return {
            key: self.dim_colour(value, brightness)
            for key, value in selected.items()
        }

    def font(self, size=11, weight="normal", size_choice=None):
        """Create a font using the currently selected text-size setting."""
        size_choice = size_choice or self.settings["size"]
        factors = {"Small": 0.85, "Medium": 1.0, "Large": 1.25}
        scaled_size = max(8, round(size * factors[size_choice]))
        return ("Segoe UI", scaled_size, weight)

    # ---------------------------------------------------------
    # APPLICATION LAYOUT AND NAVIGATION
    # ---------------------------------------------------------

    def rebuild_application(self):
        """Rebuild the application shell so applied settings affect every page."""
        if getattr(self, "fitts_stage", None) == "active":
            self.fitts_stage = "ready"
            self.fitts_started_at = None
            self.fitts_status_message = (
                "The visual settings changed during a trial. This trial was reset; "
                "click the start circle to repeat it."
            )
        for widget in self.winfo_children():
            widget.destroy()

        theme = self.get_theme()
        self.configure(bg=theme["window"])
        self.nav_buttons = {}
        self.build_layout()
        self.show_page(self.current_page)

    def build_layout(self):
        theme = self.get_theme()

        sidebar = tk.Frame(self, bg=theme["sidebar"], width=245)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="HUMAN TESTER",
            bg=theme["sidebar"],
            fg=theme["sidebar_text"],
            font=self.font(18, "bold"),
        ).pack(anchor="w", padx=22, pady=(34, 4))

        tk.Label(
            sidebar,
            text="HCI EXPERIMENT PLATFORM",
            bg=theme["sidebar"],
            fg=theme["sidebar_muted"],
            font=self.font(8, "bold"),
        ).pack(anchor="w", padx=23, pady=(0, 38))

        tk.Label(
            sidebar,
            text="MAIN MENU",
            bg=theme["sidebar"],
            fg=theme["sidebar_muted"],
            font=self.font(9, "bold"),
        ).pack(anchor="w", padx=22, pady=(0, 12))

        navigation_items = [
            "Overview",
            "Visual Controls",
            "Identification Task",
            "Target Hitting",
            "Experiment Data",
        ]

        for page_name in navigation_items:
            button = tk.Button(
                sidebar,
                text=f"  {page_name}",
                anchor="w",
                padx=12,
                pady=12,
                relief="flat",
                bd=0,
                cursor="hand2",
                font=self.font(10, "bold"),
                bg=theme["sidebar"],
                fg=theme["sidebar_text"],
                activebackground=theme["sidebar_active"],
                activeforeground=theme["sidebar_text"],
                command=lambda name=page_name: self.show_page(name),
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[page_name] = button

        tk.Label(
            sidebar,
            text="Human Performance Testing\nVersion 1.3",
            bg=theme["sidebar"],
            fg=theme["sidebar_muted"],
            font=self.font(9),
            justify="left",
        ).pack(side="bottom", anchor="w", padx=22, pady=24)

        main_area = tk.Frame(self, bg=theme["window"])
        main_area.pack(side="right", fill="both", expand=True)

        topbar = tk.Frame(main_area, bg=theme["surface"], height=72)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(
            topbar,
            text="Human Perception & Performance Tester",
            bg=theme["surface"],
            fg=theme["text"],
            font=self.font(14, "bold"),
        ).pack(side="left", padx=28)

        tk.Label(
            topbar,
            text=(
                f"{self.settings['contrast']} contrast  |  "
                f"{self.settings['size']} text  |  "
                f"{self.settings['brightness']}% brightness"
            ),
            bg=theme["surface"],
            fg=theme["muted"],
            font=self.font(9),
        ).pack(side="right", padx=24)

        self.page_container = tk.Frame(main_area, bg=theme["window"])
        self.page_container.pack(fill="both", expand=True, padx=28, pady=24)

    def show_page(self, page_name):
        if page_name != "Target Hitting" and self.fitts_stage == "active":
            self.fitts_stage = "ready"
            self.fitts_started_at = None
            self.fitts_status_message = (
                "The trial was reset because the participant left this page. "
                "Click the start circle to repeat the same trial."
            )

        self.current_page = page_name
        theme = self.get_theme()

        for widget in self.page_container.winfo_children():
            widget.destroy()

        for name, button in self.nav_buttons.items():
            button.configure(
                bg=theme["sidebar_active"] if name == page_name else theme["sidebar"]
            )

        page_builders = {
            "Overview": self.build_overview,
            "Visual Controls": self.build_visual_controls,
            "Identification Task": self.build_identification_task,
            "Target Hitting": self.build_target_hitting,
            "Experiment Data": self.build_experiment_data,
        }
        page_builders[page_name]()

    # ---------------------------------------------------------
    # REUSABLE GUI COMPONENTS
    # ---------------------------------------------------------

    def page_heading(self, title, description):
        theme = self.get_theme()
        tk.Label(
            self.page_container,
            text=title,
            bg=theme["window"],
            fg=theme["text"],
            font=self.font(23, "bold"),
        ).pack(anchor="w")

        tk.Label(
            self.page_container,
            text=description,
            bg=theme["window"],
            fg=theme["muted"],
            font=self.font(10),
            wraplength=790,
            justify="left",
        ).pack(anchor="w", pady=(6, 18))

    def create_card(self, parent, padding=18):
        theme = self.get_theme()
        return tk.Frame(
            parent,
            bg=theme["surface"],
            padx=padding,
            pady=padding,
            highlightbackground=theme["border"],
            highlightthickness=1,
        )

    def themed_label(self, parent, text, size=11, weight="normal", role="text", **kwargs):
        theme = self.get_theme()
        return tk.Label(
            parent,
            text=text,
            bg=theme["surface"],
            fg=theme[role],
            font=self.font(size, weight),
            **kwargs,
        )

    def primary_button(self, parent, text, command, **kwargs):
        theme = self.get_theme()
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=self.font(10, "bold"),
            bg=theme["primary"],
            fg=theme["primary_text"],
            activebackground=theme["primary"],
            activeforeground=theme["primary_text"],
            disabledforeground=theme["muted"],
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
            **kwargs,
        )

    # ---------------------------------------------------------
    # OVERVIEW PAGE
    # ---------------------------------------------------------

    def build_overview(self):
        theme = self.get_theme()
        self.page_heading(
            "Dashboard Overview",
            "Manage experiments, configure visual conditions and monitor human performance.",
        )

        cards_frame = tk.Frame(self.page_container, bg=theme["window"])
        cards_frame.pack(fill="x")
        for column in range(3):
            cards_frame.columnconfigure(column, weight=1)

        statistics = [
            ("EXPERIMENT TASKS", "02", "Identification and Target Hitting"),
            ("VISUAL VARIABLES", "03", "Contrast, size and brightness"),
            ("DATA STORAGE", "CSV", "Automatic result logging"),
        ]

        for column, (title, value, description) in enumerate(statistics):
            card = self.create_card(cards_frame, padding=16)
            card.grid(row=0, column=column, sticky="nsew", padx=5)
            self.themed_label(card, title, 9, "bold", "muted").pack(anchor="w")
            self.themed_label(card, value, 25, "bold", "primary").pack(anchor="w", pady=7)
            self.themed_label(card, description, 9, role="muted").pack(anchor="w")

        self.themed_label(
            self.page_container, "Experiment Modules", 15, "bold"
        ).pack(anchor="w", pady=(28, 12))

        modules = tk.Frame(self.page_container, bg=theme["window"])
        modules.pack(fill="x")
        for column in range(2):
            modules.columnconfigure(column, weight=1)

        module_details = [
            (
                "Identification Task",
                "Present an ambiguous image and collect the participant's interpretation.",
                "Identification Task",
            ),
            (
                "Target Hitting Task",
                "Measure how target size and distance affect the time needed to click a target.",
                "Target Hitting",
            ),
        ]

        for column, (title, description, destination) in enumerate(module_details):
            card = self.create_card(modules, padding=18)
            card.grid(row=0, column=column, sticky="nsew", padx=5)
            self.themed_label(card, title, 13, "bold").pack(anchor="w")
            self.themed_label(
                card, description, 10, role="muted", wraplength=300, justify="left"
            ).pack(anchor="w", pady=12)
            self.primary_button(
                card, "Open Module", lambda page=destination: self.show_page(page)
            ).pack(anchor="w")

        instructions = self.create_card(self.page_container, padding=17)
        instructions.pack(fill="x", pady=(22, 0))
        self.themed_label(instructions, "Getting Started", 12, "bold").pack(anchor="w")
        self.themed_label(
            instructions,
            "1. Configure the visual conditions.\n"
            "2. Select an experiment module.\n"
            "3. Let the participant complete the task.\n"
            "4. Record their ease-of-use rating.\n"
            "5. Review the collected experiment data.",
            10,
            role="muted",
            justify="left",
        ).pack(anchor="w", pady=(9, 0))

    # ---------------------------------------------------------
    # VISUAL CONTROLS PAGE
    # ---------------------------------------------------------

    def build_visual_controls(self):
        theme = self.get_theme()
        self.page_heading(
            "Visual Variable Controls",
            "Change contrast, text size and simulated screen brightness. "
            "Use the preview to inspect the selected conditions before applying them.",
        )

        content = tk.Frame(self.page_container, bg=theme["window"])
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=6)
        content.columnconfigure(1, weight=5)

        settings_card = self.create_card(content, padding=20)
        settings_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.themed_label(settings_card, "Contrast level", 13, "bold").pack(anchor="w")
        self.themed_label(
            settings_card,
            "Controls the distinction between text and its background.",
            9,
            role="muted",
        ).pack(anchor="w", pady=(4, 10))

        contrast_row = tk.Frame(settings_card, bg=theme["surface"])
        contrast_row.pack(anchor="w", fill="x", pady=(0, 20))
        for option in ("High", "Medium", "Low"):
            tk.Radiobutton(
                contrast_row,
                text=option,
                value=option,
                variable=self.contrast_var,
                command=self.update_preview,
                indicatoron=False,
                width=9,
                padx=8,
                pady=8,
                cursor="hand2",
                relief="solid",
                bd=1,
                font=self.font(9, "bold"),
                bg=theme["surface"],
                fg=theme["text"],
                selectcolor=theme["primary"],
                activebackground=theme["surface"],
                activeforeground=theme["text"],
            ).pack(side="left", padx=(0, 7))

        self.themed_label(settings_card, "Text and icon size", 13, "bold").pack(anchor="w")
        self.themed_label(
            settings_card,
            "Changes the size of text used throughout the application.",
            9,
            role="muted",
        ).pack(anchor="w", pady=(4, 10))

        size_row = tk.Frame(settings_card, bg=theme["surface"])
        size_row.pack(anchor="w", fill="x", pady=(0, 20))
        for option in ("Small", "Medium", "Large"):
            tk.Radiobutton(
                size_row,
                text=option,
                value=option,
                variable=self.size_var,
                command=self.update_preview,
                indicatoron=False,
                width=9,
                padx=8,
                pady=8,
                cursor="hand2",
                relief="solid",
                bd=1,
                font=self.font(9, "bold"),
                bg=theme["surface"],
                fg=theme["text"],
                selectcolor=theme["primary"],
                activebackground=theme["surface"],
                activeforeground=theme["text"],
            ).pack(side="left", padx=(0, 7))

        brightness_heading = tk.Frame(settings_card, bg=theme["surface"])
        brightness_heading.pack(fill="x")
        self.themed_label(brightness_heading, "Brightness simulation", 13, "bold").pack(side="left")

        self.brightness_value_label = self.themed_label(
            brightness_heading,
            f"{self.brightness_var.get()}%",
            11,
            "bold",
            "primary",
        )
        self.brightness_value_label.pack(side="right")

        self.themed_label(
            settings_card,
            "Adjusts the luminance of the application's colours. "
            "This does not change your physical monitor brightness.",
            9,
            role="muted",
            wraplength=410,
            justify="left",
        ).pack(anchor="w", pady=(5, 5))

        brightness_scale = tk.Scale(
            settings_card,
            from_=20,
            to=100,
            resolution=10,
            orient="horizontal",
            variable=self.brightness_var,
            command=self.on_brightness_change,
            showvalue=False,
            length=350,
            sliderlength=20,
            width=14,
            highlightthickness=0,
            bd=0,
            bg=theme["surface"],
            fg=theme["text"],
            troughcolor=theme["border"],
            activebackground=theme["primary"],
        )
        brightness_scale.pack(anchor="w", fill="x", pady=(0, 18))

        scale_labels = tk.Frame(settings_card, bg=theme["surface"])
        scale_labels.pack(fill="x", pady=(0, 18))
        self.themed_label(scale_labels, "20% · Dim", 8, role="muted").pack(side="left")
        self.themed_label(scale_labels, "100% · Full", 8, role="muted").pack(side="right")

        self.primary_button(
            settings_card, "Apply Visual Settings", self.apply_visual_settings
        ).pack(anchor="w", pady=(2, 8))

        self.themed_label(
            settings_card,
            "Your selected settings will be applied across the application.",
            9,
            role="muted",
        ).pack(anchor="w")

        preview_card = self.create_card(content, padding=20)
        preview_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self.themed_label(preview_card, "Live Preview", 14, "bold").pack(anchor="w")
        self.themed_label(
            preview_card,
            "This sample changes as you adjust the controls.",
            9,
            role="muted",
        ).pack(anchor="w", pady=(4, 14))

        self.preview_widgets = {}
        preview_panel = tk.Frame(
            preview_card,
            bg=theme["window"],
            padx=16,
            pady=18,
            highlightbackground=theme["border"],
            highlightthickness=1,
        )
        preview_panel.pack(fill="x")
        self.preview_widgets["panel"] = preview_panel

        preview_title = tk.Label(
            preview_panel,
            text="Readable interfaces matter",
            bg=theme["window"],
            fg=theme["text"],
            font=self.font(15, "bold"),
            wraplength=300,
            justify="left",
        )
        preview_title.pack(anchor="w")
        self.preview_widgets["title"] = preview_title

        preview_body = tk.Label(
            preview_panel,
            text=(
                "A clear interface helps people notice information, "
                "understand choices and complete tasks."
            ),
            bg=theme["window"],
            fg=theme["muted"],
            font=self.font(10),
            wraplength=300,
            justify="left",
        )
        preview_body.pack(anchor="w", pady=(10, 16))
        self.preview_widgets["body"] = preview_body

        preview_button = tk.Label(
            preview_panel,
            text="Example button",
            bg=theme["primary"],
            fg=theme["primary_text"],
            font=self.font(10, "bold"),
            padx=14,
            pady=9,
        )
        preview_button.pack(anchor="w")
        self.preview_widgets["button"] = preview_button

        self.preview_status = tk.Label(
            preview_card,
            text="",
            bg=theme["surface"],
            fg=theme["muted"],
            font=self.font(9),
            justify="left",
            wraplength=310,
        )
        self.preview_status.pack(anchor="w", pady=(15, 0))
        self.update_preview()

    def on_brightness_change(self, _value):
        self.brightness_value_label.configure(text=f"{self.brightness_var.get()}%")
        self.update_preview()

    def update_preview(self):
        """Update the preview while the experimenter is choosing settings."""
        if not self.preview_widgets:
            return

        selected_contrast = self.contrast_var.get()
        selected_size = self.size_var.get()
        selected_brightness = self.brightness_var.get()
        preview_theme = self.get_theme(selected_contrast, selected_brightness)

        size_factors = {"Small": 0.85, "Medium": 1.0, "Large": 1.25}
        factor = size_factors[selected_size]

        self.preview_widgets["panel"].configure(
            bg=preview_theme["window"],
            highlightbackground=preview_theme["border"],
        )
        self.preview_widgets["title"].configure(
            bg=preview_theme["window"],
            fg=preview_theme["text"],
            font=("Segoe UI", max(8, round(15 * factor)), "bold"),
        )
        self.preview_widgets["body"].configure(
            bg=preview_theme["window"],
            fg=preview_theme["muted"],
            font=("Segoe UI", max(8, round(10 * factor)), "normal"),
        )
        self.preview_widgets["button"].configure(
            bg=preview_theme["primary"],
            fg=preview_theme["primary_text"],
            font=("Segoe UI", max(8, round(10 * factor)), "bold"),
        )

        self.preview_status.configure(
            text=(
                f"Preview: {selected_contrast} contrast · {selected_size} text · "
                f"{selected_brightness}% brightness"
            )
        )

    def apply_visual_settings(self):
        """Save the chosen conditions and redraw the application with them."""
        self.settings["contrast"] = self.contrast_var.get()
        self.settings["size"] = self.size_var.get()
        self.settings["brightness"] = self.brightness_var.get()

        self.rebuild_application()
        messagebox.showinfo(
            "Visual settings applied",
            "The selected contrast, text size and brightness simulation "
            "have been applied to the application.",
            parent=self,
        )

    # ---------------------------------------------------------
    # IDENTIFICATION TASK
    # ---------------------------------------------------------

    def build_identification_task(self):
        """Build a compact identification page with the response form visible."""
        theme = self.get_theme()
        self.identification_trial_active = False
        self.identification_start_time = None
        self.identification_response_var.set("")
        self.identification_rating_var.set(0)
        self.identification_rating_buttons = []

        self.page_heading(
            "Identification Task",
            "Ask someone other than the developer to describe the ambiguous figure. "
            "Do not tell them what they should see.",
        )

        # Participant setup and trial controls stay in a compact top card.
        setup_card = self.create_card(self.page_container, padding=12)
        setup_card.pack(fill="x", pady=(0, 12))

        setup_row = tk.Frame(setup_card, bg=theme["surface"])
        setup_row.pack(fill="x")
        setup_row.columnconfigure(0, weight=1)

        participant_area = tk.Frame(setup_row, bg=theme["surface"])
        participant_area.grid(row=0, column=0, sticky="ew")
        self.themed_label(participant_area, "Participant ID", 10, "bold").pack(anchor="w")
        self.participant_entry = tk.Entry(
            participant_area,
            textvariable=self.participant_id_var,
            font=self.font(11),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=theme["border"],
            highlightcolor=theme["primary"],
            width=24,
        )
        self.participant_entry.pack(anchor="w", fill="x", ipady=5, pady=(4, 0))

        self.identification_start_button = self.primary_button(
            setup_row,
            "Start Identification Trial",
            self.start_identification_trial,
        )
        self.identification_start_button.grid(row=0, column=1, sticky="e", padx=(14, 0), pady=(17, 0))

        condition_text = (
            f"Applied condition: {self.settings['contrast']} contrast  |  "
            f"{self.settings['size']} text/figure size  |  "
            f"{self.settings['brightness']}% brightness"
        )
        self.themed_label(setup_card, condition_text, 9, role="muted").pack(anchor="w", pady=(7, 0))

        # Two-column layout keeps the image and all response controls visible
        # together instead of placing the save controls below the screen.
        task_body = tk.Frame(self.page_container, bg=theme["window"])
        task_body.pack(fill="both", expand=True)
        task_body.columnconfigure(0, weight=1, uniform="identification_columns")
        task_body.columnconfigure(1, weight=1, uniform="identification_columns")
        task_body.rowconfigure(0, weight=1)

        figure_card = self.create_card(task_body, padding=12)
        figure_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.themed_label(figure_card, "Ambiguous figure", 11, "bold").pack(anchor="w")
        self.themed_label(
            figure_card,
            "After starting, ask the participant to describe what they see. There is no right or wrong answer.",
            9,
            role="muted",
            wraplength=360,
            justify="left",
        ).pack(anchor="w", pady=(4, 8))

        self.identification_canvas = tk.Canvas(
            figure_card,
            width=360,
            height=235,
            bg=theme["surface"],
            highlightbackground=theme["border"],
            highlightthickness=1,
            bd=0,
        )
        self.identification_canvas.pack(fill="both", expand=True)
        self.identification_canvas.create_text(
            180,
            117,
            text="Click Start Identification Trial to reveal the figure.",
            fill=theme["muted"],
            font=self.font(10),
            width=320,
            justify="center",
        )

        response_card = self.create_card(task_body, padding=12)
        response_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.themed_label(response_card, "Participant response", 11, "bold").pack(anchor="w")
        self.themed_label(
            response_card,
            "Record the participant's own words. Do not suggest an answer.",
            9,
            role="muted",
            wraplength=350,
            justify="left",
        ).pack(anchor="w", pady=(4, 10))

        self.identification_response_entry = tk.Entry(
            response_card,
            textvariable=self.identification_response_var,
            font=self.font(11),
            state="disabled",
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=theme["border"],
            highlightcolor=theme["primary"],
        )
        self.identification_response_entry.pack(fill="x", ipady=7, pady=(0, 14))

        self.themed_label(
            response_card,
            "Ease of use (1 = very difficult, 5 = very easy)",
            9,
            "bold",
        ).pack(anchor="w")

        rating_row = tk.Frame(response_card, bg=theme["surface"])
        rating_row.pack(anchor="w", pady=(5, 14))
        for value in range(1, 6):
            radio = tk.Radiobutton(
                rating_row,
                text=str(value),
                value=value,
                variable=self.identification_rating_var,
                font=self.font(10, "bold"),
                state="disabled",
                bg=theme["surface"],
                fg=theme["text"],
                activebackground=theme["surface"],
                selectcolor=theme["primary"],
                padx=10,
            )
            radio.pack(side="left", padx=(0, 6))
            self.identification_rating_buttons.append(radio)

        self.identification_submit_button = self.primary_button(
            response_card,
            "Submit Response & Save",
            self.submit_identification_response,
            state="disabled",
        )
        self.identification_submit_button.pack(anchor="w", fill="x", pady=(0, 10))

        self.identification_status = tk.Label(
            response_card,
            text="Ready. Enter a participant ID and start the trial. The response and rating fields will unlock when the figure appears.",
            bg=theme["surface"],
            fg=theme["muted"],
            font=self.font(9),
            anchor="w",
            justify="left",
            wraplength=350,
        )
        self.identification_status.pack(fill="x", pady=(2, 0))

    def draw_ambiguous_figure(self):
        """Draw a Rubin-style vase / two-faces ambiguous figure."""
        if self.identification_canvas is None:
            return

        theme = self.get_theme()
        canvas = self.identification_canvas
        canvas.delete("all")
        canvas.configure(bg=theme["surface"])
        canvas.update_idletasks()

        canvas_width = max(canvas.winfo_width(), 280)
        canvas_height = max(canvas.winfo_height(), 180)
        center_x = canvas_width / 2
        center_y = canvas_height / 2

        size_factors = {"Small": 0.72, "Medium": 0.88, "Large": 1.0}
        factor = size_factors[self.settings["size"]]
        figure_width = min(380 * factor, canvas_width * 0.84)
        figure_height = min(188 * factor, canvas_height * 0.82)
        left = center_x - figure_width / 2
        top = center_y - figure_height / 2

        left_profile = [
            (0.30, 0.07), (0.35, 0.09), (0.40, 0.16), (0.43, 0.22),
            (0.46, 0.27), (0.485, 0.31), (0.445, 0.345), (0.455, 0.375),
            (0.435, 0.395), (0.45, 0.425), (0.425, 0.465), (0.39, 0.52),
            (0.35, 0.59), (0.31, 0.70), (0.25, 0.80), (0.17, 0.88),
            (0.04, 0.92),
        ]
        left_points = [(0.02, 0.04), (0.18, 0.04), (0.25, 0.055)] + left_profile + [(0.02, 0.94)]
        right_points = [(1.0 - x, y) for x, y in left_points]

        def convert(points):
            converted = []
            for x_ratio, y_ratio in points:
                converted.extend((left + x_ratio * figure_width, top + y_ratio * figure_height))
            return converted

        silhouette = theme["text"]
        canvas.create_polygon(
            *convert(left_points), fill=silhouette, outline=silhouette,
            smooth=True, splinesteps=18,
        )
        canvas.create_polygon(
            *convert(right_points), fill=silhouette, outline=silhouette,
            smooth=True, splinesteps=18,
        )

        eye_fill = theme["surface"]
        eye_width = max(4, 7 * factor)
        eye_height = max(3, 5 * factor)
        eye_y = top + 0.30 * figure_height
        for eye_x in (left + 0.265 * figure_width, left + 0.735 * figure_width):
            canvas.create_oval(
                eye_x - eye_width, eye_y - eye_height,
                eye_x + eye_width, eye_y + eye_height,
                fill=eye_fill, outline=eye_fill,
            )

    def start_identification_trial(self):
        """Display the figure and begin measuring the participant's response time."""
        participant_id = self.participant_id_var.get().strip()
        if not participant_id:
            messagebox.showwarning(
                "Participant ID required",
                "Enter a participant ID (for example, P01) before starting the trial.",
                parent=self,
            )
            self.participant_entry.focus_set()
            return

        self.identification_response_var.set("")
        self.identification_rating_var.set(0)
        self.draw_ambiguous_figure()
        self.participant_entry.configure(state="disabled")
        self.identification_response_entry.configure(state="normal")
        for radio in self.identification_rating_buttons:
            radio.configure(state="normal")

        self.update_idletasks()
        self.identification_start_time = time.perf_counter()
        self.identification_trial_active = True

        self.identification_start_button.configure(
            text="Trial in Progress",
            state="disabled",
        )
        self.identification_submit_button.configure(state="normal")
        self.identification_status.configure(
            text="The figure is visible. Enter the participant's description above, choose an ease rating (1–5), then click Submit Response & Save.",
            fg=self.get_theme()["success"],
        )
        self.identification_response_entry.focus_set()

    def submit_identification_response(self):
        """Validate, time and save one identification trial."""
        if not self.identification_trial_active or self.identification_start_time is None:
            messagebox.showwarning(
                "No active trial",
                "Start an identification trial before submitting a response.",
                parent=self,
            )
            return

        participant_id = self.participant_id_var.get().strip()
        response = self.identification_response_var.get().strip()
        rating = self.identification_rating_var.get()

        if not participant_id:
            messagebox.showwarning("Participant ID required", "Enter a participant ID.", parent=self)
            return
        if not response:
            messagebox.showwarning(
                "Response required",
                "Enter the participant's description of the figure.",
                parent=self,
            )
            self.identification_response_entry.focus_set()
            return
        if rating not in range(1, 6):
            messagebox.showwarning(
                "Ease rating required",
                "Select an ease-of-use rating from 1 to 5.",
                parent=self,
            )
            return

        elapsed = time.perf_counter() - self.identification_start_time
        condition = (
            f"{self.settings['contrast']} contrast; {self.settings['size']} size; "
            f"{self.settings['brightness']}% brightness"
        )
        result = {
            "participant_id": participant_id,
            "date_time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "visual_condition": condition,
            "task_type": "Identification",
            "response": response,
            "target_distance": "",
            "target_size": "",
            "time_taken_seconds": f"{elapsed:.3f}",
            "ease_of_use": rating,
        }

        try:
            self.save_result(result)
        except OSError as error:
            messagebox.showerror(
                "Could not save result",
                f"The result could not be written to the CSV file.\n\n{error}",
                parent=self,
            )
            return

        self.identification_trial_active = False
        self.identification_start_time = None
        self.participant_entry.configure(state="normal")
        self.identification_response_entry.configure(state="disabled")
        for radio in self.identification_rating_buttons:
            radio.configure(state="disabled")
        self.identification_submit_button.configure(state="disabled")
        self.identification_start_button.configure(
            text="Start Another Trial",
            state="normal",
        )
        self.identification_status.configure(
            text=(
                f"Result saved. Time: {elapsed:.3f} seconds | Ease rating: {rating}/5 | "
                f"File: {self.results_file.name}. You can start another trial or change visual settings."
            ),
            fg=self.get_theme()["success"],
        )
        messagebox.showinfo(
            "Identification result saved",
            f"Participant: {participant_id}\n"
            f"Time taken: {elapsed:.3f} seconds\n"
            f"Ease of use: {rating}/5\n\n"
            f"Saved to:\n{self.results_file}",
            parent=self,
        )

    # ---------------------------------------------------------
    # TARGET-HITTING TASK (FITTS' LAW)
    # ---------------------------------------------------------

    def build_target_hitting(self):
        """Build the target acquisition experiment page."""
        theme = self.get_theme()
        self.fitts_rating_buttons = []

        self.page_heading(
            "Target Hitting Task",
            "Measure how target distance and target size affect movement time. "
            "A participant first clicks the start point; a target then appears. "
            "The timer stops when the participant successfully clicks the target.",
        )

        condition_card = self.create_card(self.page_container, padding=13)
        condition_card.pack(fill="x", pady=(0, 10))
        condition_text = (
            f"Applied visual condition: {self.settings['contrast']} contrast  |  "
            f"{self.settings['size']} interface text  |  "
            f"{self.settings['brightness']}% brightness"
        )
        self.themed_label(condition_card, condition_text, 9, "bold", "primary").pack(anchor="w")
        self.themed_label(
            condition_card,
            "Target diameter is controlled separately from the interface text-size setting.",
            9,
            role="muted",
        ).pack(anchor="w", pady=(3, 0))

        participant_card = self.create_card(self.page_container, padding=13)
        participant_card.pack(fill="x", pady=(0, 10))
        participant_row = tk.Frame(participant_card, bg=theme["surface"])
        participant_row.pack(fill="x")
        participant_info = tk.Frame(participant_row, bg=theme["surface"])
        participant_info.pack(side="left", fill="x", expand=True)
        self.themed_label(participant_info, "Participant ID", 10, "bold").pack(anchor="w")
        self.themed_label(
            participant_info,
            "Use a code such as P01. Test with someone other than the developer.",
            9,
            role="muted",
        ).pack(anchor="w", pady=(2, 5))

        self.fitts_participant_entry = tk.Entry(
            participant_info,
            textvariable=self.participant_id_var,
            font=self.font(10),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=theme["border"],
            highlightcolor=theme["primary"],
        )
        self.fitts_participant_entry.pack(anchor="w", fill="x", ipady=5)

        self.fitts_session_button = self.primary_button(
            participant_row,
            "Start 12-Trial Session" if self.fitts_stage in ("idle", "complete") else "Session In Progress",
            self.start_fitts_session,
            state="normal" if self.fitts_stage in ("idle", "complete") else "disabled",
        )
        self.fitts_session_button.pack(side="right", padx=(16, 0), anchor="center")

        experiment_card = self.create_card(self.page_container, padding=12)
        experiment_card.pack(fill="x", pady=(0, 10))

        experiment_header = tk.Frame(experiment_card, bg=theme["surface"])
        experiment_header.pack(fill="x")
        self.themed_label(experiment_header, "Target acquisition area", 11, "bold").pack(side="left")

        self.fitts_trial_label = self.themed_label(
            experiment_header,
            self.fitts_current_trial_description(),
            9,
            "bold",
            "primary",
        )
        self.fitts_trial_label.pack(side="right")

        self.themed_label(
            experiment_card,
            "When ready, click the blue start circle. A target will appear to its right. "
            "Move the pointer and click the target as quickly and accurately as possible.",
            9,
            role="muted",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(4, 8))

        self.fitts_canvas = tk.Canvas(
            experiment_card,
            width=680,
            height=280,
            bg=theme["window"],
            highlightbackground=theme["border"],
            highlightthickness=1,
            bd=0,
            cursor="crosshair",
        )
        self.fitts_canvas.pack(fill="x", expand=True)
        self.fitts_canvas.bind("<Button-1>", self.handle_fitts_canvas_click)

        rating_card = self.create_card(self.page_container, padding=12)
        rating_card.pack(fill="x")
        rating_header = tk.Frame(rating_card, bg=theme["surface"])
        rating_header.pack(fill="x")
        self.themed_label(rating_header, "Participant ease-of-use rating", 10, "bold").pack(side="left")
        self.themed_label(
            rating_header,
            "1 = Very difficult     5 = Very easy",
            8,
            role="muted",
        ).pack(side="right")

        rating_row = tk.Frame(rating_card, bg=theme["surface"])
        rating_row.pack(anchor="w", pady=(5, 7))
        for value in range(1, 6):
            radio = tk.Radiobutton(
                rating_row,
                text=str(value),
                value=value,
                variable=self.fitts_rating_var,
                font=self.font(9, "bold"),
                state="disabled",
                bg=theme["surface"],
                fg=theme["text"],
                activebackground=theme["surface"],
                selectcolor=theme["primary"],
                padx=9,
            )
            radio.pack(side="left", padx=(0, 5))
            self.fitts_rating_buttons.append(radio)

        action_row = tk.Frame(rating_card, bg=theme["surface"])
        action_row.pack(fill="x")
        self.fitts_save_button = self.primary_button(
            action_row,
            "Save Result & Next Trial",
            self.save_fitts_trial,
            state="disabled",
        )
        self.fitts_save_button.pack(side="left")

        self.fitts_status_label = tk.Label(
            rating_card,
            text=self.fitts_status_message,
            bg=theme["surface"],
            fg=theme["muted"],
            font=self.font(9),
            anchor="w",
            justify="left",
            wraplength=760,
        )
        self.fitts_status_label.pack(fill="x", pady=(8, 0))

        self.restore_fitts_page_state()

    def fitts_current_trial_description(self):
        """Return a brief description of the current randomized condition."""
        if self.fitts_stage == "idle":
            return "No session started"
        if self.fitts_stage == "complete":
            return "Session complete"
        if not self.fitts_conditions or self.fitts_trial_index >= len(self.fitts_conditions):
            return "Ready"

        distance_name, distance_px, size_name, diameter = self.fitts_conditions[self.fitts_trial_index]
        return (
            f"Trial {self.fitts_trial_index + 1}/12  |  "
            f"{distance_name} ({distance_px} px)  |  "
            f"{size_name} ({diameter} px)"
        )

    def restore_fitts_page_state(self):
        """Restore the canvas, buttons and rating controls when revisiting this page."""
        if self.fitts_canvas is None:
            return

        theme = self.get_theme()
        self.fitts_canvas.configure(bg=theme["window"])
        self.fitts_canvas.delete("all")

        if self.fitts_trial_label is not None:
            self.fitts_trial_label.configure(text=self.fitts_current_trial_description())

        if self.fitts_stage == "idle":
            self.fitts_canvas.create_text(
                340,
                140,
                text="Start a session to begin the experiment.",
                fill=theme["muted"],
                font=self.font(11),
            )
        elif self.fitts_stage == "complete":
            self.fitts_canvas.create_text(
                340,
                140,
                text="Session complete! All 12 trials have been recorded.",
                fill=theme["success"],
                font=self.font(12, "bold"),
            )
        elif self.fitts_stage == "awaiting_rating":
            self.fitts_canvas.create_text(
                340,
                140,
                text=f"Target acquired in {self.fitts_elapsed:.3f} seconds",
                fill=theme["success"],
                font=self.font(13, "bold"),
            )
            for radio in self.fitts_rating_buttons:
                radio.configure(state="normal")
            self.fitts_save_button.configure(state="normal")
        else:
            self.draw_fitts_start_point()
            if self.fitts_stage == "active" and self.fitts_target_x is not None:
                self.draw_fitts_target()

        if self.fitts_session_button is not None:
            if self.fitts_stage in ("idle", "complete"):
                self.fitts_session_button.configure(
                    state="normal",
                    text="Start 12-Trial Session" if self.fitts_stage == "idle" else "Start Another Session",
                )
            else:
                self.fitts_session_button.configure(state="disabled", text="Session In Progress")

        if self.fitts_participant_entry is not None:
            self.fitts_participant_entry.configure(
                state="normal" if self.fitts_stage in ("idle", "complete") else "disabled"
            )

        if self.fitts_status_label is not None:
            status_colour = theme["success"] if self.fitts_stage in ("awaiting_rating", "complete") else theme["muted"]
            self.fitts_status_label.configure(
                text=self.fitts_status_message,
                fg=status_colour,
            )

    def start_fitts_session(self):
        """Create a randomized 12-trial schedule with three repeats per condition."""
        participant_id = self.participant_id_var.get().strip()
        if not participant_id:
            messagebox.showwarning(
                "Participant ID required",
                "Enter a participant ID (for example, P01) before starting the session.",
                parent=self,
            )
            if self.fitts_participant_entry is not None:
                self.fitts_participant_entry.focus_set()
            return

        combinations = [
            ("Short", 150, "Small", 28),
            ("Short", 150, "Large", 68),
            ("Long", 300, "Small", 28),
            ("Long", 300, "Large", 68),
        ]
        self.fitts_conditions = combinations * 3
        random.shuffle(self.fitts_conditions)
        self.fitts_trial_index = 0
        self.fitts_stage = "ready"
        self.fitts_started_at = None
        self.fitts_elapsed = None
        self.fitts_pending_result = None
        self.fitts_misses = 0
        self.fitts_rating_var.set(0)
        self.fitts_status_message = (
            "Session started. Click the blue start circle to begin trial 1 of 12. "
            "Each of the four conditions will be tested three times in randomized order."
        )

        self.fitts_participant_entry.configure(state="disabled")
        self.fitts_session_button.configure(state="disabled", text="Session In Progress")
        self.fitts_trial_label.configure(text=self.fitts_current_trial_description())
        self.restore_fitts_page_state()

    def draw_fitts_start_point(self):
        """Draw the fixed starting point for the cursor movement."""
        if self.fitts_canvas is None:
            return

        theme = self.get_theme()
        self.fitts_canvas.delete("all")
        self.fitts_canvas.update_idletasks()
        canvas_width = max(self.fitts_canvas.winfo_width(), 620)
        canvas_height = max(self.fitts_canvas.winfo_height(), 260)
        self.fitts_start_x = 90
        self.fitts_start_y = canvas_height // 2

        self.fitts_canvas.create_text(
            self.fitts_start_x,
            self.fitts_start_y + 36,
            text="START",
            fill=theme["muted"],
            font=self.font(8, "bold"),
        )
        self.fitts_canvas.create_oval(
            self.fitts_start_x - 17,
            self.fitts_start_y - 17,
            self.fitts_start_x + 17,
            self.fitts_start_y + 17,
            fill=theme["primary"],
            outline=theme["primary_text"],
            width=2,
        )
        self.fitts_canvas.create_text(
            canvas_width - 85,
            22,
            text="Click the start circle",
            fill=theme["muted"],
            font=self.font(8),
        )

    def draw_fitts_target(self):
        """Draw the target at the selected centre-to-centre pixel distance."""
        if self.fitts_canvas is None or self.fitts_target_x is None:
            return

        theme = self.get_theme()
        radius = self.fitts_target_diameter / 2
        self.fitts_canvas.create_oval(
            self.fitts_target_x - radius,
            self.fitts_target_y - radius,
            self.fitts_target_x + radius,
            self.fitts_target_y + radius,
            fill=theme["primary"],
            outline=theme["primary_text"],
            width=2,
        )

    def handle_fitts_canvas_click(self, event):
        """Handle the start-point click, target hits and target misses."""
        if self.fitts_stage == "ready":
            dx = event.x - self.fitts_start_x
            dy = event.y - self.fitts_start_y
            if (dx * dx + dy * dy) <= (22 * 22):
                self.begin_fitts_movement()
            else:
                self.fitts_status_message = "Click directly inside the blue START circle to begin the trial."
                self.fitts_status_label.configure(text=self.fitts_status_message)
            return

        if self.fitts_stage != "active":
            return

        dx = event.x - self.fitts_target_x
        dy = event.y - self.fitts_target_y
        radius = self.fitts_target_diameter / 2
        if (dx * dx + dy * dy) <= (radius * radius):
            self.complete_fitts_movement()
        else:
            self.fitts_misses += 1
            self.fitts_status_message = (
                f"That click missed the target. Keep trying. Recorded misses: {self.fitts_misses}."
            )
            self.fitts_status_label.configure(text=self.fitts_status_message)

    def begin_fitts_movement(self):
        """Reveal the target and start the movement-time clock."""
        if not self.fitts_conditions or self.fitts_trial_index >= len(self.fitts_conditions):
            return

        distance_name, distance_px, size_name, diameter = self.fitts_conditions[self.fitts_trial_index]
        canvas_width = max(self.fitts_canvas.winfo_width(), 620)
        self.fitts_target_x = self.fitts_start_x + distance_px
        self.fitts_target_y = self.fitts_start_y
        self.fitts_target_diameter = diameter

        # Keep the target fully inside the canvas if the window is resized.
        max_target_x = canvas_width - (diameter / 2) - 12
        if self.fitts_target_x > max_target_x:
            self.fitts_target_x = max_target_x

        self.fitts_misses = 0
        self.fitts_stage = "active"
        self.fitts_status_message = (
            f"Target visible: {distance_name.lower()} distance ({distance_px} px), "
            f"{size_name.lower()} target ({diameter} px). Click the target."
        )
        self.draw_fitts_start_point()
        self.draw_fitts_target()
        self.fitts_canvas.update_idletasks()
        self.fitts_started_at = time.perf_counter()
        self.fitts_status_label.configure(text=self.fitts_status_message)

    def complete_fitts_movement(self):
        """Stop the movement clock when the participant successfully hits the target."""
        if self.fitts_stage != "active" or self.fitts_started_at is None:
            return

        elapsed = time.perf_counter() - self.fitts_started_at
        distance_name, distance_px, size_name, diameter = self.fitts_conditions[self.fitts_trial_index]
        participant_id = self.participant_id_var.get().strip()
        condition = (
            f"{self.settings['contrast']} contrast; {self.settings['size']} interface text; "
            f"{self.settings['brightness']}% brightness"
        )

        self.fitts_elapsed = elapsed
        self.fitts_pending_result = {
            "participant_id": participant_id,
            "date_time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "visual_condition": condition,
            "task_type": "Target Hitting",
            "response": (
                f"Target hit; trial {self.fitts_trial_index + 1}/12; "
                f"misses before hit={self.fitts_misses}"
            ),
            "target_distance": f"{distance_name} ({distance_px} px)",
            "target_size": f"{size_name} ({diameter} px diameter)",
            "time_taken_seconds": f"{elapsed:.3f}",
            "ease_of_use": "",
        }

        self.fitts_started_at = None
        self.fitts_stage = "awaiting_rating"
        self.fitts_rating_var.set(0)
        self.fitts_canvas.delete("all")
        theme = self.get_theme()
        self.fitts_canvas.create_text(
            max(self.fitts_canvas.winfo_width(), 620) / 2,
            max(self.fitts_canvas.winfo_height(), 260) / 2,
            text=f"Target acquired!\n{elapsed:.3f} seconds",
            fill=theme["success"],
            font=self.font(15, "bold"),
            justify="center",
        )

        for radio in self.fitts_rating_buttons:
            radio.configure(state="normal")
        self.fitts_save_button.configure(state="normal")
        self.fitts_status_message = (
            f"Target hit in {elapsed:.3f} seconds. Select an ease-of-use rating, "
            "then save the result to continue."
        )
        self.fitts_status_label.configure(text=self.fitts_status_message, fg=theme["success"])

    def save_fitts_trial(self):
        """Save the completed target trial and advance to the next condition."""
        if self.fitts_stage != "awaiting_rating" or self.fitts_pending_result is None:
            return

        rating = self.fitts_rating_var.get()
        if rating not in range(1, 6):
            messagebox.showwarning(
                "Ease rating required",
                "Select an ease-of-use rating from 1 to 5 before saving this trial.",
                parent=self,
            )
            return

        result = dict(self.fitts_pending_result)
        result["ease_of_use"] = rating
        try:
            self.save_result(result)
        except OSError as error:
            messagebox.showerror(
                "Could not save result",
                f"The target-hitting result could not be written to the CSV file.\n\n{error}",
                parent=self,
            )
            return

        saved_time = float(result["time_taken_seconds"])
        self.fitts_trial_index += 1
        self.fitts_pending_result = None
        self.fitts_elapsed = None
        self.fitts_rating_var.set(0)

        for radio in self.fitts_rating_buttons:
            radio.configure(state="disabled")
        self.fitts_save_button.configure(state="disabled")

        if self.fitts_trial_index >= len(self.fitts_conditions):
            self.fitts_stage = "complete"
            self.fitts_status_message = (
                "Session complete. All 12 target-hitting trials have been saved to the CSV file. "
                "You can start another session with a new participant."
            )
            self.fitts_participant_entry.configure(state="normal")
            self.fitts_session_button.configure(state="normal", text="Start Another Session")
            self.fitts_trial_label.configure(text="Session complete")
            self.fitts_canvas.delete("all")
            theme = self.get_theme()
            self.fitts_canvas.create_text(
                max(self.fitts_canvas.winfo_width(), 620) / 2,
                max(self.fitts_canvas.winfo_height(), 260) / 2,
                text="Session complete!\n12 of 12 trials saved.",
                fill=theme["success"],
                font=self.font(15, "bold"),
                justify="center",
            )
        else:
            self.fitts_stage = "ready"
            self.fitts_status_message = (
                f"Trial saved ({saved_time:.3f} seconds, ease {rating}/5). "
                f"Prepare for trial {self.fitts_trial_index + 1} of 12, then click the start circle."
            )
            self.fitts_trial_label.configure(text=self.fitts_current_trial_description())
            self.draw_fitts_start_point()

        self.fitts_status_label.configure(text=self.fitts_status_message)

    # ---------------------------------------------------------
    # EXPERIMENT DATA PAGE
    # ---------------------------------------------------------

    def build_experiment_data(self):
        theme = self.get_theme()
        self.page_heading(
            "Experiment Data",
            "Review the CSV file that stores the results from completed experiment trials.",
        )

        card = self.create_card(self.page_container, padding=22)
        card.pack(fill="x")

        try:
            record_count = self.count_saved_results()
            status_text = f"CSV file ready · {record_count} saved experiment record(s)"
            status_colour = theme["success"]
        except OSError as error:
            status_text = f"Could not read the results file: {error}"
            status_colour = theme["danger"]

        tk.Label(
            card,
            text=status_text,
            bg=theme["surface"],
            fg=status_colour,
            font=self.font(12, "bold"),
            wraplength=730,
            justify="left",
        ).pack(anchor="w")

        self.themed_label(card, "Results file location", 10, "bold").pack(anchor="w", pady=(18, 5))
        location = tk.Label(
            card,
            text=str(self.results_file),
            bg=theme["surface"],
            fg=theme["muted"],
            font=self.font(9),
            wraplength=740,
            justify="left",
        )
        location.pack(anchor="w")

        self.themed_label(card, "Recorded fields", 10, "bold").pack(anchor="w", pady=(18, 5))
        self.themed_label(
            card,
            ", ".join(CSV_FIELDS),
            9,
            role="muted",
            wraplength=740,
            justify="left",
        ).pack(anchor="w")

        self.primary_button(
            card,
            "Refresh CSV Status",
            lambda: self.show_page("Experiment Data"),
        ).pack(anchor="w", pady=(18, 0))

        note = self.create_card(self.page_container, padding=16)
        note.pack(fill="x", pady=(14, 0))
        self.themed_label(
            note,
            "Both Identification and Target Hitting trials are now logged automatically. "
            "Target movement time is measured from target appearance to a successful target click.",
            9,
            role="muted",
            wraplength=740,
            justify="left",
        ).pack(anchor="w")

def main():
    app = HumanPerceptionTester()
    app.mainloop()


if __name__ == "__main__":
    main()
