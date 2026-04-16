from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .obfuscator import ObfuscatorError, obfuscate_path


class ToiletDuckificatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ToiletDuckificator")
        self.root.geometry("860x560")
        self.root.minsize(760, 500)
        self.root.configure(bg="#101723")

        self.selected_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Wybierz plik .py albo folder z plikami Python.")

        self._build_theme()
        self._build_layout()

    def _build_theme(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 11))
        style.configure("Card.TFrame", background="#162132")
        style.configure("Panel.TFrame", background="#122033")
        style.configure("Header.TLabel", background="#101723", foreground="#F8FAFC", font=("Segoe UI Semibold", 22))
        style.configure("Body.TLabel", background="#162132", foreground="#DBE5F0")
        style.configure("Accent.TButton", background="#12B886", foreground="#081018", padding=(18, 10), borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#19C997")])
        style.configure("Muted.TButton", background="#28415D", foreground="#F8FAFC", padding=(12, 9), borderwidth=0)
        style.map("Muted.TButton", background=[("active", "#355779")])
        style.configure("Path.TEntry", fieldbackground="#0B1420", foreground="#F8FAFC", bordercolor="#2E4259")

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, style="Panel.TFrame", padding=22)
        outer.pack(fill="both", expand=True)

        header = ttk.Label(outer, text="ToiletDuckificator", style="Header.TLabel")
        header.pack(anchor="w")

        subtitle = ttk.Label(
            outer,
            text="Obfuskacja nazw, prostych literałów i wybranych wywołań builtinów dla plików Python.",
            style="Body.TLabel",
            padding=(0, 6, 0, 20),
        )
        subtitle.pack(anchor="w")

        card = ttk.Frame(outer, style="Card.TFrame", padding=22)
        card.pack(fill="x")

        ttk.Label(card, text="Źródło", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        source_entry = ttk.Entry(card, textvariable=self.selected_path, style="Path.TEntry", width=72)
        source_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 12))

        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.grid(row=1, column=2, padx=(12, 0), pady=(6, 12), sticky="e")
        ttk.Button(buttons, text="Wybierz plik", style="Muted.TButton", command=self.pick_file).pack(fill="x")
        ttk.Button(buttons, text="Wybierz folder", style="Muted.TButton", command=self.pick_folder).pack(fill="x", pady=(10, 0))

        ttk.Label(card, text="Wyjście", style="Body.TLabel").grid(row=2, column=0, sticky="w")
        output_entry = ttk.Entry(card, textvariable=self.output_path, style="Path.TEntry", width=72)
        output_entry.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(6, 12))

        ttk.Button(card, text="Uruchom obfuskację", style="Accent.TButton", command=self.run_obfuscation).grid(
            row=4,
            column=0,
            sticky="w",
        )

        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        log_card = ttk.Frame(outer, style="Card.TFrame", padding=18)
        log_card.pack(fill="both", expand=True, pady=(18, 0))

        ttk.Label(log_card, text="Log działania", style="Body.TLabel").pack(anchor="w")
        self.log = tk.Text(
            log_card,
            wrap="word",
            bg="#0B1420",
            fg="#D7E3EF",
            insertbackground="#D7E3EF",
            relief="flat",
            height=16,
            font=("Cascadia Code", 10),
        )
        self.log.pack(fill="both", expand=True, pady=(10, 12))

        footer = ttk.Label(log_card, textvariable=self.status_text, style="Body.TLabel")
        footer.pack(anchor="w")

        self._append_log("Program zapisuje wynik do osobnej ścieżki, żeby nie nadpisać oryginałów.")

    def pick_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
        if path:
            self.selected_path.set(path)
            suggested = Path(path).with_name(f"{Path(path).stem}.duck.py")
            self.output_path.set(str(suggested))

    def pick_folder(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.selected_path.set(path)
            suggested = Path(path).with_name(f"{Path(path).name}_duckified")
            self.output_path.set(str(suggested))

    def run_obfuscation(self) -> None:
        source = self.selected_path.get().strip()
        output = self.output_path.get().strip()
        if not source:
            messagebox.showerror("Brak źródła", "Najpierw wybierz plik .py albo folder.")
            return

        self.status_text.set("Trwa obfuskacja...")
        self._append_log(f"Start: {source}")
        worker = threading.Thread(target=self._process, args=(source, output or None), daemon=True)
        worker.start()

    def _process(self, source: str, output: str | None) -> None:
        try:
            results = obfuscate_path(source, output)
        except ObfuscatorError as error:
            message = str(error)
            self.root.after(0, lambda message=message: self._handle_error(message))
            return
        except Exception as error:  # pragma: no cover - GUI safety net
            message = f"Unexpected error: {error}"
            self.root.after(0, lambda message=message: self._handle_error(message))
            return

        self.root.after(0, lambda: self._handle_success(results))

    def _handle_success(self, results: list) -> None:
        for result in results:
            marker = "changed" if result.changed else "unchanged"
            self._append_log(f"[{marker}] {result.source_path} -> {result.output_path}")
        self.status_text.set(f"Gotowe. Przetworzono {len(results)} plików.")

    def _handle_error(self, message: str) -> None:
        self.status_text.set("Operacja przerwana.")
        self._append_log(f"ERROR: {message}")
        messagebox.showerror("Błąd", message)

    def _append_log(self, message: str) -> None:
        self.log.insert("end", message + "\n")
        self.log.see("end")


def main() -> None:
    root = tk.Tk()
    app = ToiletDuckificatorApp(root)
    root.after(120, lambda: app._append_log("Wybierz plik lub folder i kliknij Uruchom obfuskację."))
    root.mainloop()


if __name__ == "__main__":
    main()
