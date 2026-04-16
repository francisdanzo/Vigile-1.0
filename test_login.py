import tkinter as tk
from desktop.main_window import COLORS, VigileEntry

root = tk.Tk()

v_user = VigileEntry(root, label="User", placeholder="admin")
v_user.pack()

v_pass = VigileEntry(root, label="Pass", placeholder="••••••••", show="•")
v_pass.pack()

def check():
    print(f"User: '{v_user.get()}', Pass: '{v_pass.get()}'")
    root.destroy()

tk.Button(root, text="Check", command=check).pack()

# Simuler type user
v_user.entry.focus_set()
v_user.entry.insert('end', 'admin')

# Simuler type pass
v_pass.entry.focus_set()
v_pass.entry.insert('end', 'admin123')

root.after(500, check)
root.mainloop()
