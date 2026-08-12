import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3, platform, subprocess, webbrowser, shutil, re, threading
from urllib.parse import quote_plus

APP="AURA Desktop Assistant"
BASE=Path(__file__).resolve().parent
DATA=BASE/"data"; DATA.mkdir(exist_ok=True)
DB=DATA/"reminders.db"; NOTES=DATA/"notes.txt"
BG="#0d1720"; PANEL="#172633"; PANEL2="#203442"; TEXT="#e8f1f5"
MUTED="#91a6b2"; ACCENT="#5eead4"; BLUE="#38bdf8"; RED="#fb7185"; GREEN="#4ade80"

class Store:
    def __init__(self):
        with sqlite3.connect(DB) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS reminders(
                id INTEGER PRIMARY KEY,title TEXT NOT NULL,when_at TEXT NOT NULL,
                done INTEGER DEFAULT 0,notified INTEGER DEFAULT 0)""")
    def add(self,title,when):
        with sqlite3.connect(DB) as c:
            x=c.execute("INSERT INTO reminders(title,when_at) VALUES(?,?)",
                        (title,when.isoformat(timespec="seconds")))
            c.commit(); return x.lastrowid
    def all(self):
        with sqlite3.connect(DB) as c:
            return c.execute("""SELECT id,title,when_at,done,notified
                                FROM reminders WHERE done=0 ORDER BY when_at""").fetchall()
    def due(self):
        now=datetime.now().isoformat(timespec="seconds")
        with sqlite3.connect(DB) as c:
            return c.execute("""SELECT id,title,when_at FROM reminders
                                WHERE done=0 AND notified=0 AND when_at<=?
                                ORDER BY when_at""",(now,)).fetchall()
    def notified(self,i):
        with sqlite3.connect(DB) as c:
            c.execute("UPDATE reminders SET notified=1 WHERE id=?",(i,)); c.commit()
    def done(self,i):
        with sqlite3.connect(DB) as c:
            c.execute("UPDATE reminders SET done=1 WHERE id=?",(i,)); c.commit()
    def delete(self,i):
        with sqlite3.connect(DB) as c:
            c.execute("DELETE FROM reminders WHERE id=?",(i,)); c.commit()

def battery():
    try:
        import psutil
        b=psutil.sensors_battery()
        if not b: return "Unavailable"
        return f"{b.percent:.0f}% • {'Charging' if b.power_plugged else 'On battery'}"
    except ImportError: return "Install psutil"
    except Exception: return "Unavailable"

def parse_when(s):
    s=re.sub(r"\s+"," ",s.strip().lower()); now=datetime.now()
    pats=[r"(tomorrow)(?: at)? (\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
          r"(today)(?: at)? (\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
          r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?"]
    for i,p in enumerate(pats):
        m=re.fullmatch(p,s)
        if not m: continue
        if i<2:
            h=int(m.group(2)); mi=int(m.group(3) or 0); ap=m.group(4)
            d=now+timedelta(days=1 if i==0 else 0)
        else:
            h=int(m.group(1)); mi=int(m.group(2) or 0); ap=m.group(3); d=now
        if ap:
            if not 1<=h<=12: raise ValueError
            h=0 if ap=="am" and h==12 else h
            h=12 if ap=="pm" and h==12 else (h+12 if ap=="pm" else h)
        if not 0<=h<=23 or not 0<=mi<=59: raise ValueError
        x=d.replace(hour=h,minute=mi,second=0,microsecond=0)
        if i==2 and x<=now: x+=timedelta(days=1)
        return x
    for f in ("%d %b %Y %H:%M","%d %B %Y %H:%M",
              "%d %b %Y %I:%M %p","%d %B %Y %I:%M %p",
              "%Y-%m-%d %H:%M","%d-%m-%Y %H:%M","%d/%m/%Y %H:%M"):
        try: return datetime.strptime(s,f)
        except ValueError: pass
    raise ValueError

def open_target(x):
    x=x.strip()
    if re.match(r"^(https?://|www\.)",x,re.I):
        webbrowser.open_new_tab(x if x.startswith("http") else "https://"+x); return f"Opening {x}"
    aliases={"chrome":"chrome","google chrome":"chrome","notepad":"notepad",
             "calculator":"calc","calc":"calc","paint":"mspaint",
             "explorer":"explorer","file explorer":"explorer","cmd":"cmd",
             "powershell":"powershell","terminal":"wt"}
    cmd=aliases.get(x.lower(),x)
    try:
        if platform.system()=="Windows": subprocess.Popen(cmd,shell=True)
        elif platform.system()=="Darwin": subprocess.Popen(["open","-a",x])
        else:
            exe=shutil.which(cmd.split()[0])
            subprocess.Popen(cmd.split() if exe else ["xdg-open",x])
        return f"Launching {x}"
    except Exception as e: return f"Could not launch {x}: {e}"

SITES={"google":"https://google.com","youtube":"https://youtube.com",
"gmail":"https://mail.google.com","maps":"https://maps.google.com",
"github":"https://github.com","chatgpt":"https://chatgpt.com",
"weather":"https://www.google.com/search?q=weather","news":"https://news.google.com"}

class AURA(tk.Tk):
    def __init__(self):
        super().__init__(); self.store=Store(); self.stop=threading.Event()
        self.title(APP); self.geometry("1160x760"); self.minsize(960,650); self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW",self.close); self.build()
        self.tick(); self.refresh_battery(); self.refresh()
        threading.Thread(target=self.monitor,daemon=True).start()

    def button(self,p,text,cmd,color=ACCENT):
        return tk.Button(p,text=text,command=cmd,bg=color,fg="#071318" if color==ACCENT else TEXT,
                         activebackground="#8af5e5",relief="flat",bd=0,
                         font=("Segoe UI",9,"bold"),padx=10,pady=8,cursor="hand2")
    def card(self,p,title):
        f=tk.Frame(p,bg=PANEL,highlightbackground="#2b3d4a",highlightthickness=1)
        tk.Label(f,text=title.upper(),bg=PANEL,fg=ACCENT,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=16,pady=(13,8))
        return f
    def build(self):
        h=tk.Frame(self,bg="#091119",height=86); h.pack(fill="x"); h.pack_propagate(False)
        tk.Label(h,text="AURA",bg="#091119",fg=ACCENT,font=("Segoe UI",25,"bold")).pack(side="left",padx=26)
        self.clock=tk.Label(h,bg="#091119",fg=TEXT,font=("Consolas",13,"bold")); self.clock.pack(side="right",padx=26)
        main=tk.Frame(self,bg=BG); main.pack(fill="both",expand=True,padx=18,pady=18)
        left=tk.Frame(main,bg=BG,width=350); left.pack(side="left",fill="y",padx=(0,14)); left.pack_propagate(False)
        right=tk.Frame(main,bg=BG); right.pack(side="right",fill="both",expand=True)
        c=self.card(left,"Command Center"); c.pack(fill="x",pady=(0,12))
        self.greet=tk.Label(c,text="",bg=PANEL,fg=TEXT,font=("Segoe UI",16,"bold"),wraplength=310,justify="left")
        self.greet.pack(anchor="w",padx=16,pady=(2,12))
        self.cmd=tk.Entry(c,bg=PANEL2,fg=TEXT,insertbackground=ACCENT,relief="flat",font=("Segoe UI",11))
        self.cmd.pack(fill="x",padx=16,ipady=10); self.cmd.bind("<Return>",lambda e:self.run())
        self.button(c,"Run command",self.run).pack(fill="x",padx=16,pady=9)
        tk.Label(c,text="Try: battery • open youtube • search AI\nor: remind me to study at 7:30 pm",
                 bg=PANEL,fg=MUTED,font=("Segoe UI",8),justify="left").pack(anchor="w",padx=16,pady=(0,14))
        c=self.card(left,"System Status"); c.pack(fill="x",pady=(0,12))
        self.bat=tk.Label(c,text="",bg=PANEL,fg=TEXT,font=("Segoe UI",12,"bold")); self.bat.pack(anchor="w",padx=16,pady=7)
        tk.Label(c,text=f"{platform.system()} • {platform.machine()}\nPython {platform.python_version()}",
                 bg=PANEL,fg=MUTED,font=("Segoe UI",9),justify="left").pack(anchor="w",padx=16,pady=(0,14))
        self.count=tk.Label(c,text="",bg=PANEL,fg=BLUE,font=("Segoe UI",10,"bold")); self.count.pack(anchor="w",padx=16,pady=(0,14))
        c=self.card(left,"Quick Actions"); c.pack(fill="x")
        g=tk.Frame(c,bg=PANEL); g.pack(fill="both",expand=True,padx=12,pady=8)
        acts=[("🌐 Internet","open internet"),("▶ YouTube","open youtube"),("🔎 Google","open google"),
              ("📁 Explorer","open explorer"),("🧮 Calculator","open calculator"),("📝 Notepad","open notepad")]
        for i,(t,cmd) in enumerate(acts):
            self.button(g,t,lambda x=cmd:self.command(x),PANEL2).grid(row=i//2,column=i%2,padx=4,pady=4,sticky="nsew")
        for i in range(2): g.columnconfigure(i,weight=1)
        c=self.card(right,"Reminder Center"); c.pack(fill="both",expand=True)
        bar=tk.Frame(c,bg=PANEL); bar.pack(fill="x",padx=14,pady=5)
        self.title_e=tk.Entry(bar,bg=PANEL2,fg=TEXT,relief="flat",font=("Segoe UI",10))
        self.title_e.insert(0,"Reminder title"); self.title_e.pack(side="left",fill="x",expand=True,ipady=8)
        self.when_e=tk.Entry(bar,bg=PANEL2,fg=TEXT,relief="flat",width=25,font=("Segoe UI",10))
        self.when_e.insert(0,"20 Aug 2026 19:30"); self.when_e.pack(side="left",padx=8,ipady=8)
        self.button(bar,"＋ Add",self.add_reminder).pack(side="left")
        frame=tk.Frame(c,bg=PANEL); frame.pack(fill="both",expand=True,padx=14,pady=8)
        self.tree=ttk.Treeview(frame,columns=("id","title","when","status"),show="headings")
        for col,head,w in [("id","#",45),("title","Reminder",330),("when","Scheduled time",200),("status","Status",130)]:
            self.tree.heading(col,text=head); self.tree.column(col,width=w,anchor="center" if col in ("id","status") else "w")
        self.tree.pack(side="left",fill="both",expand=True)
        ttk.Scrollbar(frame,orient="vertical",command=self.tree.yview).pack(side="right",fill="y")
        self.tree.configure(yscrollcommand=lambda *a:None)
        b=tk.Frame(c,bg=PANEL); b.pack(fill="x",padx=14,pady=(0,14))
        self.button(b,"✓ Mark done",self.done,GREEN).pack(side="left")
        self.button(b,"Delete",self.delete,RED).pack(side="left",padx=8)
        self.button(b,"Refresh",self.refresh,PANEL2).pack(side="right")
        self.status=tk.Label(self,bg="#091119",fg=MUTED,text="Ready.",anchor="w",font=("Segoe UI",9))
        self.status.pack(side="bottom",fill="x",ipady=7,padx=18)

    def greeting(self):
        h=datetime.now().hour
        x="Good morning" if 5<=h<12 else "Good afternoon" if h<17 else "Good evening" if h<22 else "Good night"
        return x+". How can I help?"
    def tick(self):
        self.clock.config(text=datetime.now().strftime("%A\n%d %b %Y • %I:%M:%S %p")); self.greet.config(text=self.greeting()); self.after(1000,self.tick)
    def refresh_battery(self):
        self.bat.config(text="Battery: "+battery()); self.after(30000,self.refresh_battery)
    def command(self,s): self.cmd.delete(0,"end"); self.cmd.insert(0,s); self.run()
    def run(self):
        s=self.cmd.get().strip(); self.cmd.delete(0,"end"); low=s.lower()
        if not s: return
        if low in ("help","commands"):
            self.respond("Commands:\n• battery\n• time / date\n• open internet\n• open chrome / notepad / calculator / explorer\n• open youtube / gmail / maps / github / chatgpt\n• search <query>\n• remind me to <task> at <time/date>\n• note <text> / show notes\n• system info"); return
        if low=="battery" or "battery" in low: self.respond("Battery: "+battery()); return
        if low in ("time","what time is it"): self.respond(datetime.now().strftime("It is %I:%M:%S %p.")); return
        if low in ("date","today"): self.respond(datetime.now().strftime("Today is %A, %d %B %Y.")); return
        if low in ("open internet","internet","connect to internet"):
            webbrowser.open_new_tab("https://www.google.com"); self.status.config(text="Opening the internet."); return
        m=re.match(r"^(?:search|google|look up)\s+(.+)$",s,re.I)
        if m:
            webbrowser.open_new_tab("https://www.google.com/search?q="+quote_plus(m.group(1))); self.status.config(text="Searching: "+m.group(1)); return
        m=re.match(r"^(?:open|launch|start)\s+(.+)$",s,re.I)
        if m:
            t=m.group(1).strip()
            if t.lower() in SITES: webbrowser.open_new_tab(SITES[t.lower()]); self.status.config(text="Opening "+t); return
            self.status.config(text=open_target(t)); return
        m=re.match(r"^(?:remind me|set reminder|reminder)\s+(.+?)\s+(?:at|on)\s+(.+)$",s,re.I)
        if m:
            try:
                when=parse_when(m.group(2)); 
                if when<=datetime.now(): raise ValueError
                i=self.store.add(m.group(1).strip(),when); self.refresh()
                self.respond(f"Reminder #{i} set for {when:%A, %d %B %Y at %I:%M %p}.")
            except ValueError:
                self.respond("I couldn't parse that time. Examples:\n20 Aug 2026 19:30\ntomorrow 7:00 pm\n19:45")
            return
        m=re.match(r"^(?:note|save note|remember this)\s+(.+)$",s,re.I)
        if m:
            with NOTES.open("a",encoding="utf8") as f: f.write(f"[{datetime.now():%Y-%m-%d %H:%M}] {m.group(1)}\n")
            self.respond("Saved the note."); return
        if low in ("show notes","notes"):
            self.respond(NOTES.read_text(encoding="utf8")[-2500:] if NOTES.exists() else "No notes saved."); return
        if low in ("system","system info","computer info"):
            self.respond(f"{platform.system()} {platform.release()} • {platform.machine()} • Python {platform.python_version()}"); return
        self.respond("I didn't recognize that. Type 'help' for commands.")
    def respond(self,text):
        self.status.config(text=text.replace("\n"," • "))
        w=tk.Toplevel(self); w.title("AURA"); w.geometry("520x300"); w.configure(bg=PANEL); w.transient(self)
        tk.Label(w,text="AURA",bg=PANEL,fg=ACCENT,font=("Segoe UI",13,"bold")).pack(anchor="w",padx=20,pady=(18,5))
        t=tk.Text(w,bg=PANEL2,fg=TEXT,relief="flat",wrap="word",font=("Segoe UI",10)); t.pack(fill="both",expand=True,padx=20,pady=8)
        t.insert("1.0",text); t.config(state="disabled"); self.button(w,"Close",w.destroy).pack(pady=(0,15))
    def add_reminder(self):
        title=self.title_e.get().strip(); raw=self.when_e.get().strip()
        if not title or title=="Reminder title": return messagebox.showwarning(APP,"Enter a reminder title.")
        try: when=parse_when(raw)
        except ValueError: return messagebox.showerror(APP,"Use e.g. 20 Aug 2026 19:30, tomorrow 7:00 pm, or 19:45.")
        if when<=datetime.now(): return messagebox.showwarning(APP,"Choose a future date/time.")
        self.store.add(title,when); self.title_e.delete(0,"end"); self.refresh()
    def refresh(self):
        for x in self.tree.get_children(): self.tree.delete(x)
        rows=self.store.all()
        for i,title,w,done,notified in rows:
            d=datetime.fromisoformat(w); self.tree.insert("","end",iid=str(i),values=(i,title,d.strftime("%d %b %Y • %I:%M %p"),"Notified" if notified else "Scheduled"))
        self.count.config(text=f"Active reminders: {len(rows)}")
    def selected(self):
        s=self.tree.selection(); return int(s[0]) if s else None
    def done(self):
        i=self.selected()
        if i: self.store.done(i); self.refresh()
    def delete(self):
        i=self.selected()
        if i and messagebox.askyesno(APP,"Delete selected reminder?"): self.store.delete(i); self.refresh()
    def monitor(self):
        while not self.stop.is_set():
            for i,title,w in self.store.due():
                self.store.notified(i); self.after(0,lambda t=title,w=w:self.alert(t,w))
            self.stop.wait(5)
    def alert(self,title,w):
        try: self.bell()
        except tk.TclError: pass
        messagebox.showinfo("⏰ AURA Reminder",f"{title}\n\nScheduled for:\n{w}",parent=self); self.refresh()
    def close(self):
        self.stop.set(); self.destroy()

if __name__=="__main__":
    AURA().mainloop()
