# library_final_with_admin_client_features.py
import tkinter as tk
from tkinter import messagebox, ttk
import pandas as pd
from datetime import datetime, timedelta
import os

# -----------------------
# File paths
# -----------------------
BOOKS_CSV = "books_dataset.csv"
USERS_CSV = "users.csv"
TXNS_CSV = "transactions.csv"

# -----------------------
# Penalty rule
# -----------------------
GRACE_DAYS = 10
PENALTY_PER_DAY = 5  # ₹5 per day after GRACE_DAYS
MAX_BORROW = 5       # max books per user

# -----------------------
# Load / Save helpers
# -----------------------
import pandas as pd
df = pd.read_csv("books_dataset.csv")
df.columns = ["Book ID", "Title", "Author", "Genre", "Copies"]
df.to_csv("books_dataset.csv", index=False)


def view_books():
    df = pd.read_csv("books_dataset.csv")
    print(df.head())  # for debug
    # or display in GUI

def load_or_create_csv(path, columns):
    if os.path.exists(path):
        df = pd.read_csv(path)
        # Ensure expected columns exist
        for c in columns:
            if c not in df.columns:
                df[c] = pd.NA
        return df[columns]
    else:
        return pd.DataFrame(columns=columns)

def save_df(df, path):
    df.to_csv(path, index=False)

# -----------------------
# Initialize dataframes (persistent)
# -----------------------
books = load_or_create_csv(BOOKS_CSV, ["Book ID", "Title", "Author", "Genre", "Copies"])
users = load_or_create_csv(USERS_CSV, ["User ID", "Username", "Name", "Email", "Phone", "Password"])
transactions = load_or_create_csv(TXNS_CSV, ["Transaction ID", "User ID", "Book ID",
                                             "Issue Date", "Return Date", "Status",
                                             "Penalty", "Reissue Count"])

def next_id(df, col):
    if df.empty:
        return 1
    else:
        try:
            return int(df[col].max()) + 1
        except:
            # fallback if non-numeric
            return len(df) + 1

# -----------------------
# Ensure files exist (save empty)
# -----------------------
save_df(books, BOOKS_CSV)
save_df(users, USERS_CSV)
save_df(transactions, TXNS_CSV)

# -----------------------
# Admin credentials (default)
# -----------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

# -----------------------
# Utils: date parsing and penalty
# -----------------------
def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def parse_date(s):
    if pd.isna(s) or s is None or str(s).strip() == "":
        return None
    return datetime.strptime(str(s), "%Y-%m-%d").date()

def compute_penalty(issue_date_str, return_date_str):
    issue_date = parse_date(issue_date_str)
    return_date = parse_date(return_date_str)
    if not issue_date or not return_date:
        return 0
    days = (return_date - issue_date).days
    overdue = days - GRACE_DAYS
    return int(overdue * PENALTY_PER_DAY) if overdue > 0 else 0

def compute_penalty_now(issue_date_str):
    issue_date = parse_date(issue_date_str)
    if not issue_date:
        return 0
    days = (datetime.now().date() - issue_date).days
    overdue = days - GRACE_DAYS
    return int(overdue * PENALTY_PER_DAY) if overdue > 0 else 0

def save_all():
    save_df(books, BOOKS_CSV)
    save_df(users, USERS_CSV)
    save_df(transactions, TXNS_CSV)

# -----------------------
# Core data operations
# -----------------------
def add_book_data(title, author, genre, copies):
    global books
    bid = next_id(books, "Book ID")
    books.loc[len(books)] = [bid, title, author, genre, int(copies)]
    save_all()
    return bid

def register_user_data(username, name, email, phone, password):
    global users
    if username in users["Username"].values:
        return None  # duplicate username
    uid = next_id(users, "User ID")
    users.loc[len(users)] = [uid, username, name, email, phone, password]
    save_all()
    return uid

def register_user_admin(name, email, phone, password=None):
    """
    Admin registration: create username automatically from name+uid, optional password
    Returns uid and generated username and password
    """
    global users
    uid = next_id(users, "User ID")
    # make base username from name (remove spaces, lowercase)
    base = "".join(name.strip().split()).lower() or "user"
    username_candidate = f"{base}{uid}"
    # ensure uniqueness
    while username_candidate in users["Username"].values:
        uid += 1
        username_candidate = f"{base}{uid}"
    if not password:
        password = f"pass{uid}"
    users.loc[len(users)] = [uid, username_candidate, name, email, phone, password]
    save_all()
    return uid, username_candidate, password

def issue_book_data(user_id, book_id):
    global transactions, books
    # validations
    if book_id not in books["Book ID"].values:
        return False, "Book ID not found."
    if user_id not in users["User ID"].values:
        return False, "User ID not found."

    # Borrowing rules:
    # 1) Max 5 books
    currently_borrowed = transactions[
        (transactions["User ID"] == user_id) & (transactions["Status"] == "Issued")
    ].shape[0]
    if currently_borrowed >= MAX_BORROW:
        return False, f"Borrowing limit reached ({MAX_BORROW})."

    # 2) Cannot borrow if any overdue book
    user_issued = transactions[
        (transactions["User ID"] == user_id) & (transactions["Status"] == "Issued")
    ]
    for _, row in user_issued.iterrows():
        # compute if overdue now
        pen = compute_penalty_now(row["Issue Date"])
        if pen > 0:
            return False, "You have overdue book(s). Return them before borrowing."

    bidx = books[books["Book ID"] == book_id].index[0]
    if int(books.at[bidx, "Copies"]) <= 0:
        return False, "No copies available."
    # proceed
    books.at[bidx, "Copies"] = int(books.at[bidx, "Copies"]) - 1
    tid = next_id(transactions, "Transaction ID")
    transactions.loc[len(transactions)] = [tid, user_id, book_id, today_str(), "", "Issued", 0, 0]
    save_all()
    return True, f"Issued. Transaction ID: {tid}"

def return_book_data(transaction_id):
    global transactions, books
    if transaction_id not in transactions["Transaction ID"].values:
        return False, "Transaction not found."
    tidx = transactions[transactions["Transaction ID"] == transaction_id].index[0]
    if transactions.at[tidx, "Status"] == "Returned":
        return False, "Already returned."
    # update return date
    transactions.at[tidx, "Return Date"] = today_str()
    transactions.at[tidx, "Status"] = "Returned"
    # compute penalty
    pen = compute_penalty(transactions.at[tidx, "Issue Date"], transactions.at[tidx, "Return Date"])
    transactions.at[tidx, "Penalty"] = pen
    # restore book copy
    book_id = int(transactions.at[tidx, "Book ID"])
    bidx = books[books["Book ID"] == book_id].index[0]
    books.at[bidx, "Copies"] = int(books.at[bidx, "Copies"]) + 1
    save_all()
    return True, f"Returned. Penalty: ₹{pen}"

def reissue_book_data(transaction_id):
    global transactions
    if transaction_id not in transactions["Transaction ID"].values:
        return False, "Transaction not found."
    tidx = transactions[transactions["Transaction ID"] == transaction_id].index[0]
    if transactions.at[tidx, "Status"] != "Issued":
        return False, "Transaction is not currently issued."
    transactions.at[tidx, "Issue Date"] = today_str()
    transactions.at[tidx, "Reissue Count"] = int(transactions.at[tidx, "Reissue Count"]) + 1
    save_all()
    return True, "Reissued: new issue date is today."

# -----------------------
# New user/member utilities
# -----------------------
def search_user(keyword):
    """Search users by name or email (case-insensitive). Returns DataFrame."""
    kw = str(keyword).strip().lower()
    if kw == "":
        return users.copy()
    res = users[
        users["Name"].str.lower().str.contains(kw, na=False) |
        users["Email"].str.lower().str.contains(kw, na=False)
    ]
    return res

def update_user(user_id, name=None, email=None, phone=None, password=None):
    """Update user fields if provided. Returns True/False and message."""
    global users
    if user_id not in users["User ID"].values:
        return False, "User ID not found."
    idx = users[users["User ID"] == user_id].index[0]
    if name: users.at[idx, "Name"] = name
    if email: users.at[idx, "Email"] = email
    if phone: users.at[idx, "Phone"] = phone
    if password: users.at[idx, "Password"] = password
    save_all()
    return True, "User updated."

def delete_username(user_id):
    """Delete user. Also optionally warn if outstanding issued books."""
    global users, transactions
    if user_id not in users["User ID"].values:
        return False, "User ID not found."
    # Check outstanding issued books
    outstanding = transactions[(transactions["User ID"] == user_id) & (transactions["Status"] == "Issued")]
    if not outstanding.empty:
        return False, "User has outstanding issued books. Cannot delete."
    users = users[users["User ID"] != user_id].reset_index(drop=True)
    # also remove transaction rows (historical) — keep history? here we'll keep history but mark user removed; for safety we keep transactions
    save_all()
    return True, "User deleted."

def user_browsing_history(user_id):
    """Return transactions DataFrame for a user."""
    return transactions[transactions["User ID"] == user_id].sort_values(by="Issue Date", ascending=False)

def view_statistics():
    """Return a dictionary of stats."""
    total_users = users.shape[0]
    total_books = books["Copies"].astype(int).sum() if not books.empty else 0
    total_titles = books.shape[0]
    total_issued = transactions[transactions["Status"] == "Issued"].shape[0]
    total_penalties = int(transactions["Penalty"].dropna().astype(int).sum()) if not transactions.empty else 0
    stats = {
        "total_users": total_users,
        "total_titles": total_titles,
        "total_copies_available": total_books,
        "currently_issued": total_issued,
        "penalties_collected_total": total_penalties
    }
    return stats

# -----------------------
# GUI: login -> role dashboards
# -----------------------
def open_login_window():
    global login_window, admin_user_entry, admin_pass_entry, client_user_entry, client_pass_entry
    login_window = tk.Tk()
    login_window.title("Library Login")
    login_window.geometry("440x440")

    tk.Label(login_window, text="📚 Library Management System", font=("Arial", 16, "bold")).pack(pady=12)
    tabs = ttk.Notebook(login_window)

    # Admin tab
    admin_tab = ttk.Frame(tabs)
    tabs.add(admin_tab, text="Admin")
    tk.Label(admin_tab, text="Admin Username").pack(pady=4)
    admin_user_entry = tk.Entry(admin_tab); admin_user_entry.pack()
    tk.Label(admin_tab, text="Password").pack(pady=4)
    admin_pass_entry = tk.Entry(admin_tab, show="*"); admin_pass_entry.pack()
    tk.Button(admin_tab, text="Login", command=admin_login, bg="lightblue").pack(pady=10)

    # Client tab
    client_tab = ttk.Frame(tabs)
    tabs.add(client_tab, text="Client")
    tk.Label(client_tab, text="Username").pack(pady=4)
    client_user_entry = tk.Entry(client_tab); client_user_entry.pack()
    tk.Label(client_tab, text="Password").pack(pady=4)
    client_pass_entry = tk.Entry(client_tab, show="*"); client_pass_entry.pack()
    tk.Button(client_tab, text="Login", command=client_login, bg="lightgreen").pack(pady=8)
    tk.Label(client_tab, text="New here?").pack(pady=6)
    tk.Button(client_tab, text="Sign up", command=open_signup_window, bg="orange").pack()

    tabs.pack(expand=1, fill="both")
    login_window.mainloop()

# -----------------------
# Role dashboards and UI components
# -----------------------
def reopen_login(current_root):
    current_root.destroy()
    open_login_window()

# Admin UI
def admin_dashboard():
    global admin_root
    login_window.destroy()
    admin_root = tk.Tk()
    admin_root.title("Admin Dashboard")
    admin_root.geometry("1000x700")

    tk.Label(admin_root, text="👑 Admin Dashboard", font=("Arial", 18, "bold")).pack(pady=8)

    # Buttons frame
    btn_frame = tk.Frame(admin_root)
    btn_frame.pack(pady=6)
    tk.Button(btn_frame, text="Add Book", width=16, command=lambda: add_book_ui(admin_root), bg="lightblue").grid(row=0, column=0, padx=6)
    tk.Button(btn_frame, text="Issue Book", width=16, command=lambda: issue_book_ui(admin_root), bg="orange").grid(row=0, column=1, padx=6)
    tk.Button(btn_frame, text="Return Book", width=16, command=lambda: return_book_ui(admin_root), bg="lightpink").grid(row=0, column=2, padx=6)
    tk.Button(btn_frame, text="Register New Member", width=18, command=lambda: register_member_admin_ui(admin_root), bg="lightgreen").grid(row=0, column=3, padx=6)
    tk.Button(btn_frame, text="Search Member", width=14, command=lambda: search_member_ui(admin_root), bg="khaki").grid(row=0, column=4, padx=6)
    tk.Button(btn_frame, text="Manage Members", width=14, command=lambda: manage_members_ui(admin_root), bg="salmon").grid(row=0, column=5, padx=6)
    tk.Button(btn_frame, text="View Statistics", width=14, command=lambda: view_statistics_ui(admin_root), bg="lightgray").grid(row=0, column=6, padx=6)
    tk.Button(btn_frame, text="Transactions Report", width=16, command=lambda: show_transactions(admin_root), bg="gray").grid(row=0, column=7, padx=6)
    tk.Button(btn_frame, text="Logout", width=10, command=lambda: reopen_login(admin_root), bg="darkgray").grid(row=0, column=8, padx=6)

    # Quick tables
    tk.Label(admin_root, text="Books Overview:", font=("Arial", 13, "bold")).pack(pady=6)
    show_books_table(admin_root)

    admin_root.mainloop()

def add_book_ui(parent):
    win = tk.Toplevel(parent)
    win.title("Add Book")
    win.geometry("380x320")

    tk.Label(win, text="Add New Book", font=("Arial", 13, "bold")).pack(pady=8)
    tk.Label(win, text="Title").pack(); title = tk.Entry(win); title.pack()
    tk.Label(win, text="Author").pack(); author = tk.Entry(win); author.pack()
    tk.Label(win, text="Genre").pack(); genre = tk.Entry(win); genre.pack()
    tk.Label(win, text="Copies").pack(); copies = tk.Entry(win); copies.pack()

    def do_add():
        t,a,g,c = title.get().strip(), author.get().strip(), genre.get().strip(), copies.get().strip()
        if not (t and a and g and c and c.isdigit()):
            messagebox.showerror("Error", "Fill all fields correctly (copies as number)."); return
        bid = add_book_data(t,a,g,int(c))
        messagebox.showinfo("Done", f"Added Book ID {bid}")
        win.destroy()
        refresh_books_table(parent)

    tk.Button(win, text="Add", command=do_add, bg="lightblue").pack(pady=10)

def issue_book_ui(parent):
    win = tk.Toplevel(parent)
    win.title("Issue Book")
    win.geometry("360x240")
    tk.Label(win, text="Issue Book (Admin)", font=("Arial", 13, "bold")).pack(pady=8)
    tk.Label(win, text="User ID").pack(); uid = tk.Entry(win); uid.pack()
    tk.Label(win, text="Book ID").pack(); bid = tk.Entry(win); bid.pack()

    def do_issue():
        try:
            u = int(uid.get().strip()); b = int(bid.get().strip())
        except:
            messagebox.showerror("Error", "Enter valid integer IDs"); return
        ok,msg = issue_book_data(u,b)
        if ok:
            messagebox.showinfo("Done", msg); win.destroy(); refresh_books_table(parent)
        else:
            messagebox.showerror("Error", msg)

    tk.Button(win, text="Issue", command=do_issue, bg="orange").pack(pady=10)

def return_book_ui(parent):
    win = tk.Toplevel(parent)
    win.title("Return Book")
    win.geometry("320x220")
    tk.Label(win, text="Return Book (Admin)", font=("Arial", 13, "bold")).pack(pady=8)
    tk.Label(win, text="Transaction ID").pack(); tid = tk.Entry(win); tid.pack()

    def do_return():
        try:
            t = int(tid.get().strip())
        except:
            messagebox.showerror("Error", "Enter valid Transaction ID"); return
        ok,msg = return_book_data(t)
        if ok:
            messagebox.showinfo("Done", msg); win.destroy(); refresh_books_table(parent)
        else:
            messagebox.showerror("Error", msg)

    tk.Button(win, text="Return", command=do_return, bg="lightpink").pack(pady=10)

def show_books_table(parent):
    # frame name to identify and replace
    # remove old frame if exists
    for w in parent.pack_slaves():
        if isinstance(w, tk.Frame) and w.winfo_name()=="books_frame":
            w.destroy()
    frame = tk.Frame(parent, name="books_frame")
    frame.pack(fill="both", expand=False, padx=8, pady=8)
    cols = list(books.columns)
    tree = ttk.Treeview(frame, columns=cols, show="headings", height=6)
    for c in cols: 
        tree.heading(c, text=c)
        tree.column(c, width=120 if c!="Title" else 260)
    for _, r in books.iterrows(): tree.insert("", "end", values=list(r))
    tree.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

def refresh_books_table(parent):
    # refresh by re-rendering
    show_books_table(parent)

def show_transactions(parent):
    win = tk.Toplevel(parent)
    win.title("Transactions Report")
    win.geometry("1100x500")
    tk.Label(win, text="Transactions", font=("Arial", 13, "bold")).pack(pady=8)
    cols = list(transactions.columns)
    tree = ttk.Treeview(win, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=130)
    for _, r in transactions.iterrows():
        tree.insert("", "end", values=list(r))
    tree.pack(fill="both", expand=True)

# Admin: register member UI
def register_member_admin_ui(parent):
    win = tk.Toplevel(parent)
    win.title("Register Member (Admin)")
    win.geometry("380x360")
    tk.Label(win, text="Register New Member", font=("Arial", 13, "bold")).pack(pady=8)
    tk.Label(win, text="Full Name").pack(); name_e = tk.Entry(win); name_e.pack()
    tk.Label(win, text="Email").pack(); email_e = tk.Entry(win); email_e.pack()
    tk.Label(win, text="Phone").pack(); phone_e = tk.Entry(win); phone_e.pack()
    tk.Label(win, text="Password (optional)").pack(); pass_e = tk.Entry(win, show="*"); pass_e.pack()
    def do_reg():
        name = name_e.get().strip(); email = email_e.get().strip(); phone = phone_e.get().strip(); pwd = pass_e.get().strip()
        if not (name and email and phone):
            messagebox.showerror("Error", "Fill name, email, phone"); return
        uid, uname, upass = register_user_admin(name, email, phone, pwd if pwd else None)
        messagebox.showinfo("Done", f"Member created.\nUser ID: {uid}\nUsername: {uname}\nPassword: {upass}\n(Share these with user)")
        win.destroy()
    tk.Button(win, text="Create Member", command=do_reg, bg="lightgreen").pack(pady=10)

# Admin: search member UI
def search_member_ui(parent):
    win = tk.Toplevel(parent)
    win.title("Search Member")
    win.geometry("700x450")
    tk.Label(win, text="Search Member by Name or Email", font=("Arial", 13, "bold")).pack(pady=8)
    q = tk.Entry(win, width=60); q.pack(pady=6)
    cols = ["User ID", "Username", "Name", "Email", "Phone"]
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for c in cols: tree.heading(c, text=c); tree.column(c, width=140)
    tree.pack(fill="both", expand=True, padx=6, pady=6)
    def do_search():
        df = search_user(q.get().strip())
        for row in tree.get_children(): tree.delete(row)
        for _, r in df.iterrows():
            tree.insert("", "end", values=[r["User ID"], r["Username"], r["Name"], r["Email"], r["Phone"]])
    tk.Button(win, text="Search", command=do_search, bg="khaki").pack(pady=6)
    do_search()

# Admin: manage members (update/delete)
def manage_members_ui(parent):
    win = tk.Toplevel(parent)
    win.title("Manage Members")
    win.geometry("900x500")
    tk.Label(win, text="Manage Members (Select to Edit/Delete)", font=("Arial", 13, "bold")).pack(pady=8)
    cols = ["User ID", "Username", "Name", "Email", "Phone"]
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for c in cols: tree.heading(c, text=c); tree.column(c, width=160)
    for _, r in users.iterrows():
        tree.insert("", "end", values=[r["User ID"], r["Username"], r["Name"], r["Email"], r["Phone"]])
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    selected_idx = {"value": None}
    def on_select(event):
        sel = tree.selection()
        if not sel:
            selected_idx["value"] = None
            return
        vals = tree.item(sel[0])["values"]
        selected_idx["value"] = int(vals[0])

    tree.bind("<<TreeviewSelect>>", on_select)

    # update form
    frm = tk.Frame(win); frm.pack(pady=6)
    tk.Label(frm, text="Name").grid(row=0,column=0); name_e = tk.Entry(frm); name_e.grid(row=0,column=1)
    tk.Label(frm, text="Email").grid(row=1,column=0); email_e = tk.Entry(frm); email_e.grid(row=1,column=1)
    tk.Label(frm, text="Phone").grid(row=2,column=0); phone_e = tk.Entry(frm); phone_e.grid(row=2,column=1)
    tk.Label(frm, text="Password").grid(row=3,column=0); pass_e = tk.Entry(frm); pass_e.grid(row=3,column=1)

    def fill_fields():
        uid = selected_idx["value"]
        if not uid:
            messagebox.showerror("Error","Select a user first"); return
        row = users[users["User ID"]==uid].iloc[0]
        name_e.delete(0,tk.END); name_e.insert(0,row["Name"])
        email_e.delete(0,tk.END); email_e.insert(0,row["Email"])
        phone_e.delete(0,tk.END); phone_e.insert(0,row["Phone"])

    def do_update():
        uid = selected_idx["value"]
        if not uid:
            messagebox.showerror("Error","Select a user first"); return
        ok,msg = update_user(uid, name=name_e.get().strip() or None, email=email_e.get().strip() or None, phone=phone_e.get().strip() or None, password=pass_e.get().strip() or None)
        if ok:
            messagebox.showinfo("Done", msg); win.destroy()
        else:
            messagebox.showerror("Error", msg)

    def do_delete():
        uid = selected_idx["value"]
        if not uid:
            messagebox.showerror("Error","Select a user first"); return
        confirm = messagebox.askyesno("Confirm", "Are you sure you want to delete this user? (Requires no outstanding books)")
        if not confirm: return
        ok,msg = delete_username(uid)
        if ok:
            messagebox.showinfo("Done", msg); win.destroy()
        else:
            messagebox.showerror("Error", msg)

    tk.Button(frm, text="Fill Fields", command=fill_fields, bg="lightgray").grid(row=4,column=0,padx=6,pady=6)
    tk.Button(frm, text="Update User", command=do_update, bg="lightgreen").grid(row=4,column=1,padx=6,pady=6)
    tk.Button(frm, text="Delete User", command=do_delete, bg="salmon").grid(row=4,column=2,padx=6,pady=6)

# Admin: view stats UI
def view_statistics_ui(parent):
    stats = view_statistics()
    msg = (
        f"Total users: {stats['total_users']}\n"
        f"Total book titles: {stats['total_titles']}\n"
        f"Total copies available (sum): {stats['total_copies_available']}\n"
        f"Currently issued books: {stats['currently_issued']}\n"
        f"Total penalties recorded: ₹{stats['penalties_collected_total']}\n"
    )
    messagebox.showinfo("Statistics", msg)

# -----------------------
# Client Dashboard and UI
# -----------------------
def client_dashboard(username):
    # find name for welcome
    user_row = users[users["Username"]==username].iloc[0]
    login_window.destroy()
    client_root = tk.Tk()
    client_root.title(f"Client Dashboard - {user_row['Name']}")
    client_root.geometry("1000x700")

    tk.Label(client_root, text=f"👤 Welcome {user_row['Name']}", font=("Arial", 16, "bold")).pack(pady=8)

    # buttons
    btnf = tk.Frame(client_root); btnf.pack()
    tk.Button(btnf, text="Search Books", width=18, command=lambda: client_search_ui(client_root), bg="lightblue").grid(row=0,column=0,padx=6,pady=6)
    tk.Button(btnf, text="My Borrowing History", width=20, command=lambda: client_history_ui(client_root, int(user_row["User ID"])), bg="lightgreen").grid(row=0,column=1,padx=6,pady=6)
    tk.Button(btnf, text="Issue Book", width=18, command=lambda: client_issue_ui(client_root, int(user_row["User ID"])), bg="orange").grid(row=0,column=2,padx=6,pady=6)
    tk.Button(btnf, text="Return Book", width=22, command=lambda: client_return_ui(client_root, int(user_row["User ID"])), bg="lightpink").grid(row=0,column=3,padx=6,pady=6)
    tk.Button(btnf, text="Instructions", width=18, command=lambda: client_instructions_ui(client_root), bg="lightyellow").grid(row=0,column=4,padx=6,pady=6)
    tk.Button(btnf, text="Logout", width=12, command=lambda: reopen_login(client_root), bg="gray").grid(row=0,column=5,padx=6,pady=6)

    # show quick view
    tk.Label(client_root, text="Available Books (quick view):", font=("Arial", 12, "bold")).pack(pady=6)
    show_books_table(client_root)

    client_root.mainloop()

def client_search_ui(parent):
    win = tk.Toplevel(parent); win.title("Search Books"); win.geometry("850x500")
    tk.Label(win, text="Search Books (title/author/genre)", font=("Arial", 13, "bold")).pack(pady=8)
    q = tk.Entry(win, width=60); q.pack(pady=6)
    cols = list(books.columns)
    tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
    for c in cols: tree.heading(c, text=c); tree.column(c, width=150 if c!="Title" else 300)
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    def do_search():
        kw = q.get().lower().strip()
        if kw=="":
            df = books
        else:
            df = books[books["Title"].str.lower().str.contains(kw, na=False) |
                       books["Author"].str.lower().str.contains(kw, na=False) |
                       books["Genre"].str.lower().str.contains(kw, na=False)]
        for row in tree.get_children(): tree.delete(row)
        for _, r in df.iterrows(): tree.insert("", "end", values=list(r))

    tk.Button(win, text="Search", command=do_search, bg="lightblue").pack(pady=6)
    do_search()

def client_issue_ui(parent, user_id):
    win = tk.Toplevel(parent); win.title("Issue Book"); win.geometry("360x260")
    tk.Label(win, text="Issue Book (Client)", font=("Arial", 13, "bold")).pack(pady=8)
    tk.Label(win, text="Book ID").pack(); bid_e = tk.Entry(win); bid_e.pack()
    def do_issue():
        try:
            bid = int(bid_e.get().strip())
        except:
            messagebox.showerror("Error","Enter valid Book ID"); return
        ok,msg = issue_book_data(user_id, bid)
        if ok:
            messagebox.showinfo("Done", msg); win.destroy()
        else:
            messagebox.showerror("Error", msg)
    tk.Button(win, text="Issue", command=do_issue, bg="orange").pack(pady=10)

def client_history_ui(parent, user_id):
    win = tk.Toplevel(parent); win.title("My Borrowing History"); win.geometry("1000x500")
    tk.Label(win, text="My Borrowing History (all transactions)", font=("Arial", 13, "bold")).pack(pady=8)
    cols = list(transactions.columns)
    tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
    for c in cols: tree.heading(c, text=c); tree.column(c, width=130)
    user_txns = transactions[transactions["User ID"]==user_id].sort_values("Issue Date", ascending=False)
    for _, r in user_txns.iterrows(): tree.insert("", "end", values=list(r))
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    # actions: select txn id then return or reissue
    def selected_tid():
        sel = tree.selection()
        if not sel: return None
        vals = tree.item(sel[0])["values"]
        return int(vals[0])

    def do_return():
        tid = selected_tid()
        if not tid: messagebox.showerror("Error","Select a transaction"); return
        ok,msg = return_book_data(tid)
        if ok:
            messagebox.showinfo("Done", msg); win.destroy()
        else:
            messagebox.showerror("Error", msg)

    def do_reissue():
        tid = selected_tid()
        if not tid: messagebox.showerror("Error","Select a transaction"); return
        ok,msg = reissue_book_data(tid)
        if ok:
            messagebox.showinfo("Done", msg); win.destroy()
        else:
            messagebox.showerror("Error", msg)

    af = tk.Frame(win); af.pack(pady=6)
    tk.Button(af, text="Return Selected", command=do_return, bg="lightpink").grid(row=0,column=0,padx=6)
    tk.Button(af, text="Reissue Selected", command=do_reissue, bg="lightgreen").grid(row=0,column=1,padx=6)

def client_return_ui(parent, user_id):
    # reuse the history UI selection or allow entering txn id
    win = tk.Toplevel(parent); win.title("Return Book"); win.geometry("360x220")
    tk.Label(win, text="Return Book (Client)", font=("Arial", 13, "bold")).pack(pady=8)
    tk.Label(win, text="Transaction ID (from your history)").pack(); tid = tk.Entry(win); tid.pack()
    def do_return():
        try:
            t = int(tid.get().strip())
        except:
            messagebox.showerror("Error", "Enter valid Transaction ID"); return
        # ensure transaction belongs to this user
        if t not in transactions["Transaction ID"].values:
            messagebox.showerror("Error", "Transaction not found"); return
        row = transactions[transactions["Transaction ID"]==t].iloc[0]
        if int(row["User ID"]) != user_id:
            messagebox.showerror("Error", "This transaction does not belong to you"); return
        ok,msg = return_book_data(t)
        if ok:
            messagebox.showinfo("Done", msg); win.destroy()
        else:
            messagebox.showerror("Error", msg)
    tk.Button(win, text="Return", command=do_return, bg="lightpink").pack(pady=10)

def client_instructions_ui(parent):
    win = tk.Toplevel(parent); win.title("Instructions"); win.geometry("420x280")
    msg = (
        "Client instructions:\n\n"
        f"• You can issue a book by Book ID (if copies available and you meet rules).\n"
        f"• Borrowing rules: Max {MAX_BORROW} books at a time. Cannot borrow with overdue books.\n"
        f"• Return by selecting your transaction and clicking Return.\n"
        f"• Reissue resets issue date to today (extended due period).\n"
        f"• Penalty = ₹{PENALTY_PER_DAY}/day after {GRACE_DAYS} days.\n"
    )
    tk.Label(win, text=msg, justify="left", wraplength=380).pack(padx=12, pady=12)

# -----------------------
# Signup / Login handlers
# -----------------------
def open_signup_window():
    win = tk.Toplevel(login_window); win.title("Signup"); win.geometry("380x420")
    tk.Label(win, text="Create Account", font=("Arial", 14, "bold")).pack(pady=8)
    tk.Label(win, text="Name").pack(); name_e = tk.Entry(win); name_e.pack()
    tk.Label(win, text="Username").pack(); user_e = tk.Entry(win); user_e.pack()
    tk.Label(win, text="Email").pack(); email_e = tk.Entry(win); email_e.pack()
    tk.Label(win, text="Phone").pack(); phone_e = tk.Entry(win); phone_e.pack()
    tk.Label(win, text="Password").pack(); pass_e = tk.Entry(win, show="*"); pass_e.pack()
    def do_signup():
        name = name_e.get().strip(); username = user_e.get().strip()
        email = email_e.get().strip(); phone = phone_e.get().strip(); pwd = pass_e.get().strip()
        if not (name and username and email and phone and pwd):
            messagebox.showerror("Error","Fill all fields"); return
        uid = register_user_data(username, name, email, phone, pwd)
        if uid is None:
            messagebox.showerror("Error","Username already taken"); return
        messagebox.showinfo("Success", f"Account created. Your User ID: {uid}")
        win.destroy()
    tk.Button(win, text="Sign Up", command=do_signup, bg="lightgreen").pack(pady=10)

def admin_login():
    u = admin_user_entry.get().strip(); p = admin_pass_entry.get().strip()
    if u==ADMIN_USERNAME and p==ADMIN_PASSWORD:
        admin_dashboard()
    else:
        messagebox.showerror("Error","Invalid Admin credentials")

def client_login():
    username = client_user_entry.get().strip(); pwd = client_pass_entry.get().strip()
    if username not in users["Username"].values:
        messagebox.showerror("Error","Username not found")
        return
    user_row = users[users["Username"]==username].iloc[0]
    if user_row["Password"] != pwd:
        messagebox.showerror("Error","Incorrect password")
        return
    client_dashboard(username)

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    open_login_window()
