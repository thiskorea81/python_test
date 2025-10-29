import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
from db_connection import connect, bootstrap_admin
from dotenv import load_dotenv

# ---- 환경변수 로드 ----
load_dotenv()

# ---- 해시 유틸(데모용) ----
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

DEFAULT_ADMIN_ID = "admin"
DEFAULT_ADMIN_PW = "admin"  # 최초 로그인 시 변경 강제 권장


class Session:
    client = None
    db = None


class LoginWindow(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=16)
        self.grid(sticky="nsew")

        master.title("상담 프로그램 로그인")
        master.geometry("360x220")

        ttk.Label(self, text="아이디").grid(row=0, column=0, sticky="e", pady=6)
        self.ent_id = ttk.Entry(self, width=28)
        self.ent_id.grid(row=0, column=1, sticky="w")

        ttk.Label(self, text="비밀번호").grid(row=1, column=0, sticky="e", pady=6)
        self.ent_pw = ttk.Entry(self, show="*", width=28)
        self.ent_pw.grid(row=1, column=1, sticky="w")

        ttk.Button(self, text="로그인", command=self.on_login).grid(row=2, column=0, columnspan=2, pady=(12, 0))
        master.bind("<Return>", lambda e: self.on_login())

        self.try_connect_db()

    def try_connect_db(self):
        """환경변수 기반 DB 자동 연결"""
        try:
            Session.client, Session.db = connect()
            bootstrap_admin(
                Session.db,
                admin_username=DEFAULT_ADMIN_ID,
                admin_password_hash=sha256(DEFAULT_ADMIN_PW),
                hash_ready=True,
            )
            print("✅ MongoDB 연결 성공 (환경변수 기반)")
        except Exception as e:
            messagebox.showerror("DB 연결 실패", f"MongoDB 연결에 실패했습니다.\n{e}")
            self.master.destroy()

    def on_login(self):
        if Session.db is None:
            messagebox.showwarning("확인", "DB 연결이 설정되지 않았습니다.")
            return

        users = Session.db["users"]
        uid = self.ent_id.get().strip()
        pw = self.ent_pw.get().strip()
        u = users.find_one({"username": uid})
        if not u or u.get("password_hash") != sha256(pw):
            messagebox.showerror("로그인 실패", "아이디 또는 비밀번호가 올바르지 않습니다.")
            return
        messagebox.showinfo("로그인 성공", f"{uid} 로그인 성공 (role={u.get('role')})")


def main():
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()