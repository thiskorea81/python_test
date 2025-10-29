# 파일: app.py
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from db_connection import connect, bootstrap_admin

"""
Tkinter 애플리케이션 (환경변수 기반 MongoDB 자동 연결)
- 로그인 → (최초 로그인 시 비밀번호 변경 강제) → 역할별 홈
- 관리자 홈: TSV/XLSX 업로드(학생/교사) → 미리보기 → DB 저장
- 계정 규칙:
  * 학생: username=학번, 기본 비밀번호 a1234567!, 최초 변경 필요
  * 교사: username=이름(중복 시 이름1, 이름2..), 기본 비밀번호 t1234567!, 최초 변경 필요
  * 관리자: admin/admin (최초 변경 필요)
"""

# ---- 환경변수 로드 ----
load_dotenv()

# ---- 해시 유틸(데모용) ----
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

DEFAULT_ADMIN_ID = "admin"
DEFAULT_ADMIN_PW = "admin"  # 최초 로그인 시 변경 권장
DEFAULT_STUDENT_PW = "a1234567!"
DEFAULT_TEACHER_PW = "t1234567!"

# ---- 전역 세션 ----
class Session:
    client = None
    db = None

# ==========================
# 비밀번호 변경 다이얼로그
# ==========================
class ChangePasswordDialog(tk.Toplevel):
    def __init__(self, master, username: str):
        super().__init__(master)
        self.title("비밀번호 변경")
        self.resizable(False, False)
        self.username = username

        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0)

        ttk.Label(frm, text=f"사용자: {username}").grid(row=0, column=0, columnspan=2, sticky='w', pady=(0,8))
        ttk.Label(frm, text="새 비밀번호").grid(row=1, column=0, sticky='e', pady=4)
        self.ent_new = ttk.Entry(frm, show='*', width=28)
        self.ent_new.grid(row=1, column=1, sticky='w')

        ttk.Label(frm, text="확인").grid(row=2, column=0, sticky='e', pady=4)
        self.ent_conf = ttk.Entry(frm, show='*', width=28)
        self.ent_conf.grid(row=2, column=1, sticky='w')

        ttk.Button(frm, text="변경", command=self.on_change).grid(row=3, column=0, columnspan=2, pady=(10,0))
        self.bind('<Return>', lambda e: self.on_change())
        self.grab_set()

    def on_change(self):
        new = self.ent_new.get()
        conf = self.ent_conf.get()
        if not new or len(new) < 8:
            messagebox.showwarning('확인', '비밀번호는 8자 이상 권장합니다.')
            return
        if new != conf:
            messagebox.showwarning('확인', '비밀번호 확인이 일치하지 않습니다.')
            return
        Session.db['users'].update_one(
            {'username': self.username},
            {'$set': {'password_hash': sha256(new), 'must_change_pw': False}}
        )
        messagebox.showinfo('완료', '비밀번호가 변경되었습니다.')
        self.destroy()

# ==========================
# 로그인 창
# ==========================
class LoginWindow(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=16)
        self.grid(sticky='nsew')
        master.title('상담 프로그램 로그인')
        master.geometry('360x220')

        # DB 자동 연결
        self.try_connect_db()

        ttk.Label(self, text='아이디').grid(row=0, column=0, sticky='e', pady=6)
        self.ent_id = ttk.Entry(self, width=28)
        self.ent_id.grid(row=0, column=1, sticky='w')

        ttk.Label(self, text='비밀번호').grid(row=1, column=0, sticky='e', pady=6)
        self.ent_pw = ttk.Entry(self, show='*', width=28)
        self.ent_pw.grid(row=1, column=1, sticky='w')

        ttk.Button(self, text='로그인', command=self.on_login).grid(row=2, column=0, columnspan=2, pady=(12,0))
        master.bind('<Return>', lambda e: self.on_login())

    def try_connect_db(self):
        try:
            Session.client, Session.db = connect()  # .env 기반
            # admin 기본 계정 부트스트랩(없으면 생성)
            bootstrap_admin(Session.db, admin_username=DEFAULT_ADMIN_ID,
                            admin_password_hash=sha256(DEFAULT_ADMIN_PW), hash_ready=True)
            print('✅ MongoDB 연결 성공 (.env)')
        except Exception as e:
            messagebox.showerror('DB 연결 실패', f'MongoDB 연결에 실패했습니다.{e}')
            self.master.destroy()

    def on_login(self):
        users = Session.db['users']
        uid = self.ent_id.get().strip()
        pw = self.ent_pw.get().strip()
        u = users.find_one({'username': uid})
        if not u or u.get('password_hash') != sha256(pw):
            messagebox.showerror('로그인 실패', '아이디 또는 비밀번호가 올바르지 않습니다.')
            return
        if u.get('must_change_pw', False):
            ChangePasswordDialog(self, uid).wait_window()
            # 재확인
            u = users.find_one({'username': uid})
            if u.get('must_change_pw', False):
                return
        role = u.get('role', 'user')
        if role == 'admin':
            AdminHome.open(self.master, uid)
        elif role == 'teacher':
            UserHome.open(self.master, uid, role='teacher')
        else:
            UserHome.open(self.master, uid, role='student')

# ==========================
# 공용/교사용/학생용 홈 (스켈레톤)
# ==========================
class UserHome(tk.Toplevel):
    @classmethod
    def open(cls, master, username: str, role: str):
        win = cls(master, username, role)
        win.grab_set()

    def __init__(self, master, username: str, role: str):
        super().__init__(master)
        self.title(f"{role.upper()} 홈 - {username}")
        self.geometry('560x360')
        ttk.Label(self, text=f"환영합니다, {username} ({role})", font=('', 12, 'bold')).pack(pady=12)
        ttk.Label(self, text='※ 상담 조회/등록, 내 정보 변경 등은 이후 추가').pack()

# ==========================
# 관리자 홈: TSV/XLSX 업로드 → 저장
# ==========================
class AdminHome(tk.Toplevel):
    @classmethod
    def open(cls, master, username: str):
        win = cls(master, username)
        win.grab_set()

    def __init__(self, master, username: str):
        super().__init__(master)
        self.username = username
        self.title(f"관리자 홈 - {username}")
        self.geometry('860x600')

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True)

        self.tab_upload = ttk.Frame(nb)
        nb.add(self.tab_upload, text='학생/교사 업로드')
        self.build_upload_tab(self.tab_upload)

    def build_upload_tab(self, parent):
        top = ttk.Frame(parent, padding=8)
        top.pack(fill='x')

        ttk.Label(top, text='대상').pack(side='left')
        self.cmb_target = ttk.Combobox(top, values=['학생', '교사'], state='readonly', width=8)
        self.cmb_target.current(0)
        self.cmb_target.pack(side='left', padx=6)

        ttk.Button(top, text='파일 선택(.tsv/.xlsx)', command=self.on_pick_file).pack(side='left', padx=6)
        ttk.Button(top, text='DB 저장', command=self.on_save_to_db).pack(side='left', padx=6)

        self.status = tk.StringVar(value='파일을 선택하세요.')
        ttk.Label(parent, textvariable=self.status, foreground='#444', padding=(8,4)).pack(anchor='w')

        cols = ('index', 'preview')
        self.tree = ttk.Treeview(parent, columns=cols, show='headings', height=20)
        self.tree.heading('index', text='#')
        self.tree.heading('preview', text='행 미리보기')
        self.tree.column('index', width=40, anchor='center')
        self.tree.column('preview', width=800, anchor='w')
        self.tree.pack(fill='both', expand=True, padx=8, pady=6)

        self.loaded_df: Optional[pd.DataFrame] = None

        note = (
            "컬럼 가이드 (권장)"
            "- 학생: student_id(학번), name(이름), class(반) 등"
            "- 교사: name(이름), phone(연락처) 등"
            "※ 계정 생성 필수 컬럼: 학생=student_id/name, 교사=name"
        )
        ttk.Label(parent, text=note, foreground='#666').pack(anchor='w', padx=8, pady=(0,8))

    def on_pick_file(self):
        path = filedialog.askopenfilename(
            title='TSV 또는 XLSX 선택',
            filetypes=[('TSV', '*.tsv'), ('Excel', '*.xlsx'), ('All', '*.*')]
        )
        if not path:
            return
        try:
            if path.lower().endswith('.tsv'):
                df = pd.read_csv(path, sep='	')
            elif path.lower().endswith('.xlsx'):
                df = pd.read_excel(path)
            else:
                raise ValueError('지원하지 않는 파일 형식입니다.')
            self.loaded_df = df
            self.refresh_preview(df)
            self.status.set(f"불러오기 완료: {len(df)}행")
        except Exception as e:
            messagebox.showerror('오류', f'파일을 불러오지 못했습니다.{e}')

    def refresh_preview(self, df: pd.DataFrame, max_rows: int = 300):
        for i in self.tree.get_children():
            self.tree.delete(i)
        preview_cols = list(df.columns)
        for idx, row in df.head(max_rows).iterrows():
            row_as_text = ", ".join([f"{c}={row.get(c)}" for c in preview_cols])
            self.tree.insert('', 'end', values=(idx+1, row_as_text))

    def on_save_to_db(self):
        if self.loaded_df is None:
            messagebox.showwarning('확인', '먼저 파일을 불러오세요.')
            return
        target = self.cmb_target.get()
        df = self.loaded_df.fillna('')
        try:
            if target == '학생':
                self._save_students(df)
            else:
                self._save_teachers(df)
            messagebox.showinfo('완료', f'{target} 데이터가 저장되었습니다.')
        except Exception as e:
            messagebox.showerror('에러', f'저장 실패: {e}')

    def _save_students(self, df: pd.DataFrame):
        def pick(df_cols, *names):
            for n in names:
                if n in df_cols:
                    return n
            return None
        cols = list(df.columns)
        col_id = pick(cols, 'student_id', '학번', 'id', 'ID', 'studentId')
        col_name = pick(cols, 'name', '이름', 'student_name')
        if not col_id or not col_name:
            raise ValueError("학생 업로드에는 '학번/student_id'와 '이름/name' 컬럼이 필요합니다.")

        users = Session.db['users']
        students = Session.db['students']
        inserted = 0
        for _, r in df.iterrows():
            sid = str(r[col_id]).strip()
            name = str(r[col_name]).strip()
            if not sid or not name:
                continue
            doc = r.to_dict()
            doc['student_id'] = sid
            doc['name'] = name
            students.update_one({'student_id': sid}, {'$set': doc}, upsert=True)
            if users.count_documents({'username': sid}) == 0:
                users.insert_one({
                    'username': sid,
                    'role': 'student',
                    'password_hash': sha256(DEFAULT_STUDENT_PW),
                    'must_change_pw': True,
                })
            inserted += 1
        self.status.set(f'학생 저장 완료: {inserted}건')

    def _save_teachers(self, df: pd.DataFrame):
        def pick(df_cols, *names):
            for n in names:
                if n in df_cols:
                    return n
            return None
        cols = list(df.columns)
        col_name = pick(cols, 'name', '이름', 'teacher_name')
        if not col_name:
            raise ValueError("교사 업로드에는 '이름/name' 컬럼이 필요합니다.")

        users = Session.db['users']
        teachers = Session.db['teachers']
        inserted = 0
        for _, r in df.iterrows():
            name = str(r[col_name]).strip()
            if not name:
                continue
            # 교사 상세 저장(이름 키로 upsert)
            doc = r.to_dict()
            doc['name'] = name
            teachers.update_one({'name': name}, {'$set': doc}, upsert=True)

            # username 충돌 처리: 이름, 이름1, 이름2 ...
            base = name
            username = base
            k = 1
            while users.count_documents({'username': username}) > 0:
                username = f"{base}{k}"
                k += 1

            if users.count_documents({'username': username}) == 0:
                users.insert_one({
                    'username': username,
                    'role': 'teacher',
                    'password_hash': sha256(DEFAULT_TEACHER_PW),
                    'must_change_pw': True,
                })
            inserted += 1
        self.status.set(f'교사 저장 완료: {inserted}건')

# ==========================
# 엔트리 포인트
# ==========================

def main():
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()

if __name__ == '__main__':
    main()
