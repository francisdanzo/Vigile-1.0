import tkinter as tk
from desktop.main_window import COLORS, VigileEntry

root = tk.Tk()

v_user = VigileEntry(root, label="User", placeholder="admin")
v_user.pack()

def check():
    print(f"DEBUG _is_placeholder_active: {v_user._is_placeholder_active}")
    print(f"DEBUG actual entry content: '{v_user.entry.get()}'")
    print(f"DEBUG VigileEntry.get(): '{v_user.get()}'")
    root.destroy()

tk.Button(root, text="Check", command=check).pack()

def simulate():
    print("Simulating focus in...")
    v_user.entry.event_generate("<FocusIn>")
    print("Simulating typing 'admin'...")
    v_user.entry.insert(0, 'admin')
    print("Simulating focus out...")
    v_user.entry.event_generate("<FocusOut>")
    check()

root.after(500, simulate)
root.mainloop()
