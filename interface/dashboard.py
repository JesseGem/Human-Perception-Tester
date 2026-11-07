import tkinter as tk
from tkinter import ttk


class Dashboard:
    """A lightweight Tk-based dashboard for a human perception test app.

    In headless test environments, the class gracefully falls back to a no-op
    implementation so importing and basic smoke tests can run without a display.
    """

    def __init__(self, title: str = "Human Perception Tester", width: int = 1000, height: int = 700):
        self.title = title
        self.width = width
        self.height = height
        self.root = None
        self.headless = False
        self._startup_error = None
        self._setup_root()

    def _setup_root(self):
        try:
            self.root = tk.Tk()
            self.root.title(self.title)
            self.root.geometry(f"{self.width}x{self.height}")
            self.root.minsize(self.width, self.height)
            self.root.configure(bg="#f5f5f5")
            self._build_ui()
        except Exception as exc:  # pragma: no cover - exercised in headless CI.
            self.headless = True
            self._startup_error = exc
            self.root = None

    def _build_ui(self):
        if self.root is None:
            return

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        container = ttk.Frame(self.root, padding=20)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        title = ttk.Label(container, text=self.title, font=("Segoe UI", 20, "bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 10))

        description = ttk.Label(
            container,
            text="Prepare a perception task, record responses, and evaluate the participant.",
            wraplength=700,
            justify="left",
        )
        description.grid(row=1, column=0, sticky="w")

        content = ttk.Frame(container, padding=(0, 20, 0, 0))
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)

        self.status = ttk.Label(content, text="Ready to begin", foreground="#1f6feb")
        self.status.grid(row=0, column=0, sticky="w")

        self.start_button = ttk.Button(content, text="Start Test")
        self.start_button.grid(row=1, column=0, sticky="w", pady=(12, 0))

    def mainloop(self):
        if self.root is not None and not self.headless:
            self.root.mainloop()

    def destroy(self):
        if self.root is not None:
            self.root.destroy()
            self.root = None

    def __getattr__(self, name):
        if self.root is not None:
            return getattr(self.root, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


if __name__ == "__main__":
    app = Dashboard()
    app.mainloop()
