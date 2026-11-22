import os, sys, sqlite3, json, traceback
from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton,
 QComboBox, QCheckBox, QScrollArea, QFrame, QMenu, QDialog, QFormLayout, QSpinBox,
 QTimeEdit, QSystemTrayIcon, QMessageBox, QListWidget, QDialogButtonBox, QTextEdit, QInputDialog)
from PySide6.QtCore import QTime

APP='QuickTasksPython'  # Keep existing data folder to preserve tasks
DISPLAY_NAME='HelloTasks'
DATA=Path(os.environ.get('APPDATA',str(Path.home()))) / APP
DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'tasks.db'

class Store:
 def __init__(self):
  self.db=sqlite3.connect(DB)
  self.db.row_factory=sqlite3.Row
  self.db.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, tag TEXT DEFAULT "Untagged", done INTEGER DEFAULT 0, created TEXT NOT NULL, completed TEXT, recurring_id INTEGER)')
  self.db.execute('CREATE TABLE IF NOT EXISTS recurring (id INTEGER PRIMARY KEY, title TEXT NOT NULL, tag TEXT, frequency TEXT, interval_n INTEGER, weekday INTEGER, hour INTEGER, minute INTEGER, next_due TEXT, active INTEGER DEFAULT 1)')
  self.db.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, title TEXT, tag TEXT, completed TEXT)')
  self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
  columns=[r[1] for r in self.db.execute("PRAGMA table_info(tasks)")]
  if "note" not in columns:self.db.execute("ALTER TABLE tasks ADD COLUMN note TEXT DEFAULT ''")
  self.db.commit()
 def rows(self,sql,args=()):return self.db.execute(sql,args).fetchall()
 def run(self,sql,args=()):
  c=self.db.execute(sql,args);self.db.commit();return c.lastrowid
 def get(self,key,default):
  row=self.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
  return json.loads(row['value']) if row else default
 def set(self,key,val):self.run('INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)',(key,json.dumps(val)))
 def add(self,title,tag='Untagged',recurring_id=None,note=''):
  return self.run('INSERT INTO tasks(title,tag,created,recurring_id,note) VALUES(?,?,?,?,?)',(title,tag,datetime.now().isoformat(timespec='seconds'),recurring_id,note))
 def complete(self,task_id,done):
  task=self.rows('SELECT * FROM tasks WHERE id=?',(task_id,))[0]
  now=datetime.now().isoformat(timespec='seconds') if done else None
  self.run('UPDATE tasks SET done=?,completed=? WHERE id=?',(int(done),now,task_id))
  if done and not task['done']:self.run('INSERT INTO history(title,tag,completed) VALUES(?,?,?)',(task['title'],task['tag'],now))
 def tick(self):
  now=datetime.now(); changed=False
  for r in self.rows('SELECT * FROM recurring WHERE active=1'):
   due=datetime.fromisoformat(r['next_due']); count=0
   while due<=now and count<100:
    self.add(r['title'],r['tag'],r['id']);changed=True;count+=1
    if r['frequency']=='Daily':due+=timedelta(days=r['interval_n'])
    else:due+=timedelta(weeks=r['interval_n'])
   if count:self.run('UPDATE recurring SET next_due=? WHERE id=?',(due.isoformat(timespec='seconds'),r['id']))
  return changed

LIGHT_STYLE="""
QWidget {background:#f8fafc;color:#182338;font-family:'Segoe UI';font-size:12px;}
QDialog {background:#f8fafc;}
QLabel {background:transparent;}
QLabel#heading {font-size:16px;font-weight:700;color:#111827;}
QLabel#muted {color:#78869a;font-size:11px;}
QLabel#section {color:#64748b;font-size:11px;font-weight:700;}
QLabel#taskTitle {color:#172033;font-size:12px;font-weight:600;}
QLabel#tagChip {background:#e9f7f4;color:#087e72;border-radius:5px;padding:1px 5px;font-size:10px;}
QLabel#noteText {color:#6a7688;font-size:11px;}
QFrame#task {background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;}
QFrame#task[done="true"] {background:#f1f5f9;border:1px solid #e2e8f0;}
QFrame#divider {background:#e7edf3;max-height:1px;min-height:1px;}
QLineEdit,QComboBox,QTextEdit {background:#ffffff;border:1px solid #dce4ed;border-radius:7px;padding:5px;color:#17243a;selection-background-color:#cceee8;}
QLineEdit:focus,QTextEdit:focus {border:1px solid #0d9488;}
QPushButton {background:#ffffff;border:1px solid #e1e7ef;border-radius:9px;padding:8px 11px;color:#344054;}
QPushButton:hover {background:#edf4f7;}
QPushButton#primary {background:#0f8278;border:1px solid #0f8278;color:white;font-weight:600;padding:4px;}
QPushButton#primary:hover {background:#0c7068;}
QPushButton#iconButton {background:transparent;border:0;color:#8994a6;padding:3px;font-size:18px;}
QPushButton#iconButton:hover {background:#edf3f7;color:#344054;}
QPushButton#footer {background:transparent;border:0;color:#68778b;font-size:11px;padding:2px;}
QPushButton#footer:hover {background:#eaf0f6;}
QPushButton#restoreButton {padding:4px 12px;min-height:22px;}
QScrollArea {border:0;background:transparent;}
QScrollArea > QWidget > QWidget {background:transparent;}
QMenu {background:#ffffff;border:1px solid #dce3ec;}
QMenu::item {padding:8px 20px;}
QMenu::item:selected {background:#e8f7f5;}
QCheckBox {background:transparent;spacing:8px;}
QScrollBar:vertical {background:transparent;width:6px;}
QScrollBar::handle:vertical {background:#cbd5e1;border-radius:3px;min-height:24px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
"""
DARK_STYLE="""
QWidget {background:#171c26;color:#e8edf6;font-family:'Segoe UI';font-size:12px;}
QDialog {background:#171c26;}
QLabel {background:transparent;}
QLabel#heading {font-size:16px;font-weight:700;color:#f8fafc;}
QLabel#muted {color:#9ba9ba;font-size:11px;}
QLabel#section {color:#a1adbd;font-size:11px;font-weight:700;}
QLabel#taskTitle {color:#f1f5f9;font-size:12px;font-weight:600;}
QLabel#tagChip {background:#173f3d;color:#70e4d6;border-radius:5px;padding:1px 5px;font-size:10px;}
QLabel#noteText {color:#9aa8ba;font-size:11px;}
QFrame#task {background:#242c3a;border:1px solid #354154;border-radius:8px;}
QFrame#task[done="true"] {background:#202733;border:1px solid #354154;}
QFrame#divider {background:#30394a;max-height:1px;min-height:1px;}
QLineEdit,QComboBox,QTextEdit {background:#242c3a;border:1px solid #394558;border-radius:7px;padding:5px;color:#e8edf6;}
QLineEdit:focus,QTextEdit:focus {border:1px solid #2dd4bf;}
QPushButton {background:#283243;border:1px solid #3b485c;border-radius:9px;padding:8px 11px;color:#e8edf6;}
QPushButton:hover {background:#364358;}
QPushButton#primary {background:#0f766e;border:1px solid #0f766e;color:white;font-weight:600;padding:4px;}
QPushButton#primary:hover {background:#0d9488;}
QPushButton#iconButton {background:transparent;border:0;color:#9ba9ba;padding:3px;font-size:18px;}
QPushButton#iconButton:hover {background:#364358;}
QPushButton#footer {background:transparent;border:0;color:#a4b1c1;font-size:11px;padding:2px;}
QPushButton#footer:hover {background:#283243;}
QPushButton#restoreButton {padding:4px 12px;min-height:22px;}
QScrollArea {border:0;background:transparent;}
QScrollArea > QWidget > QWidget {background:transparent;}
QMenu {background:#242c3a;border:1px solid #394558;}
QMenu::item {padding:8px 20px;}
QMenu::item:selected {background:#0f766e;}
QCheckBox {background:transparent;spacing:8px;}
QScrollBar:vertical {background:transparent;width:6px;}
QScrollBar::handle:vertical {background:#475569;border-radius:3px;min-height:24px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
"""

class TaskDialog(QDialog):
 def __init__(self,parent=None,task=None):
  super().__init__(parent)
  self.setWindowTitle('Edit Task' if task else 'Add Task');self.setMinimumWidth(340)
  layout=QVBoxLayout(self)
  layout.addWidget(QLabel('Task'))
  self.task=QLineEdit(task['title'] if task else '');self.task.setPlaceholderText('What needs to be done?');layout.addWidget(self.task)
  layout.addWidget(QLabel('Tag'))
  self.tag=QLineEdit(task['tag'] if task else '');self.tag.setPlaceholderText('e.g. Work');layout.addWidget(self.tag)
  layout.addWidget(QLabel('Note'))
  self.note=QTextEdit();self.note.setPlaceholderText('Optional details');self.note.setFixedHeight(85)
  if task:self.note.setPlainText(task['note'] or '')
  layout.addWidget(self.note)
  buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
  buttons.accepted.connect(self.validate);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
  self.task.setFocus()
 def validate(self):
  if not self.task.text().strip():
   QMessageBox.warning(self,'Task required','Please enter a task.');return
  self.accept()
 def values(self):return self.task.text().strip(),self.tag.text().strip().lstrip('#') or 'Untagged',self.note.toPlainText().strip()

class TaskbarWidget(QWidget):
 def __init__(self,main):
  super().__init__(None);self.main=main
  self.setWindowTitle('HelloTasks mini widget')
  self.setWindowFlags(Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
  self.setStyleSheet(self.main.theme_style())
  self.resize(290,270)
  layout=QVBoxLayout(self);layout.setContentsMargins(9,9,9,9)
  header=QHBoxLayout();header.addWidget(QLabel('✓  HelloTasks'));header.addStretch()
  add=QPushButton('+');add.setFixedWidth(30);add.clicked.connect(self.main.open_add_dialog);header.addWidget(add)
  restore=QPushButton('↗');restore.setFixedWidth(30);restore.setToolTip('Open main window');restore.clicked.connect(self.restore);header.addWidget(restore)
  hide=QPushButton('×');hide.setFixedWidth(30);hide.clicked.connect(self.hide);header.addWidget(hide)
  layout.addLayout(header)
  self.scroll=QScrollArea();self.scroll.setWidgetResizable(True)
  self.holder=QWidget();self.items=QVBoxLayout(self.holder);self.items.setContentsMargins(0,0,0,0)
  self.scroll.setWidget(self.holder);layout.addWidget(self.scroll)
 def update_tasks(self):
  self.main.clear_layout(self.items)
  tasks=self.main.store.rows('SELECT * FROM tasks WHERE done=0 ORDER BY id DESC')
  for t in tasks:
   row=QHBoxLayout();cb=QCheckBox();cb.toggled.connect(lambda checked,tid=t['id']:self.main.toggle(tid,checked));row.addWidget(cb)
   label=QLabel(t['title']);label.setWordWrap(True);label.setToolTip(t['note'] or '');row.addWidget(label,1)
   container=QWidget();container.setLayout(row);self.items.addWidget(container)
  if not tasks:self.items.addWidget(QLabel('No active tasks'))
  self.items.addStretch()
 def show_near_taskbar(self):
  self.update_tasks()
  screen=QApplication.primaryScreen()
  if screen:
   rect=screen.availableGeometry()
   self.move(rect.right()-self.width()-12,rect.bottom()-self.height()-10)
  self.show();self.raise_()
 def restore(self):self.hide();self.main.show_main()

class SettingsDialog(QDialog):
 def __init__(self,store,parent=None):
  super().__init__(parent);self.store=store;self.setWindowTitle('Preferences');self.setMinimumWidth(350)
  f=QVBoxLayout(self);f.setSpacing(13);f.setContentsMargins(20,20,20,20)
  f.addWidget(QLabel('Appearance'))
  self.theme=QComboBox();self.theme.addItems(['Light','Dark']);self.theme.setCurrentText(store.get('theme','Light'));f.addWidget(self.theme)
  self.top=QCheckBox('Keep window always on top');self.top.setChecked(store.get('top',True));f.addWidget(self.top)
  self.hot=QCheckBox('Global shortcut: Ctrl + Alt + Space');self.hot.setChecked(store.get('hotkey',True));f.addWidget(self.hot)
  self.start=QCheckBox('Launch when Windows starts');self.start.setChecked(store.get('startup',False));f.addWidget(self.start)
  self.mini=QCheckBox('Start minimized');self.mini.setChecked(store.get('minimized',False));f.addWidget(self.mini)
  # Developer credit is intentionally placed in Settings to keep the task list minimal.
  credit=QLabel('Built with ❤️ in India by <a href="https://github.com/itsrajmaurya">Raj Maurya</a>')
  credit.setObjectName('muted')
  credit.setAlignment(Qt.AlignCenter)
  credit.setTextFormat(Qt.RichText)
  credit.setOpenExternalLinks(True)
  credit.setToolTip('Visit Raj Maurya on GitHub')
  f.addWidget(credit)
  b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);b.accepted.connect(self.save);b.rejected.connect(self.reject);f.addWidget(b)
 def save(self):
  self.store.set('theme',self.theme.currentText())
  for key,widget in [('top',self.top),('hotkey',self.hot),('startup',self.start),('minimized',self.mini)]:self.store.set(key,widget.isChecked())
  self.accept()

class Bridge(QObject):focus=Signal()

class Main(QWidget):
 def __init__(self):
  super().__init__();self.store=Store();self.bridge=Bridge();self.bridge.focus.connect(self.focus_entry);self.hotkey_registered=False
  self.setWindowTitle(DISPLAY_NAME);self.resize(345,570);self.setMinimumSize(315,390)
  self.setStyleSheet(self.theme_style());self.apply_top()
  self.make_ui();self.mini_widget=TaskbarWidget(self);self.make_tray();self.configure_hotkey();self.refresh()
  
  if self.store.get('minimized',False):QTimer.singleShot(100,self.minimize_to_widget_on_start)
 def theme_style(self):return DARK_STYLE if self.store.get('theme','Light')=='Dark' else LIGHT_STYLE
 def minimize_to_widget_on_start(self):self.hide();self.mini_widget.show_near_taskbar()
 def apply_top(self):
  self.setWindowFlag(Qt.WindowStaysOnTopHint,self.store.get('top',True))
 def make_ui(self):
  outer=QVBoxLayout(self);outer.setContentsMargins(14,14,14,9);outer.setSpacing(8)
  heading=QHBoxLayout();heading.setSpacing(6)
  name=QLabel(DISPLAY_NAME);name.setObjectName('heading');heading.addWidget(name);heading.addStretch()
  self.count=QLabel('');self.count.setObjectName('muted');heading.addWidget(self.count);outer.addLayout(heading)
  # Compact header: no subtitle
  add_button=QPushButton('＋  Add task');add_button.setObjectName('primary');add_button.setFixedHeight(32);add_button.clicked.connect(self.open_add_dialog);outer.addWidget(add_button)
  filterrow=QHBoxLayout();filterrow.setSpacing(6)
  self.tag_filter=QComboBox();self.status_filter=QComboBox();self.status_filter.addItems(['Active','All tasks'])
  self.tag_filter.setToolTip('Filter by tag');self.status_filter.setToolTip('Filter by status')
  self.tag_filter.currentIndexChanged.connect(self.refresh_tasks);self.status_filter.currentIndexChanged.connect(self.refresh_tasks)
  filterrow.addWidget(self.tag_filter,1);filterrow.addWidget(self.status_filter,1);outer.addLayout(filterrow)
  self.section=QLabel('YOUR TASKS');self.section.setObjectName('section');outer.addWidget(self.section)
  self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
  self.holder=QWidget();self.tasks_layout=QVBoxLayout(self.holder);self.tasks_layout.setContentsMargins(1,2,3,2);self.tasks_layout.setSpacing(6)
  self.scroll.setWidget(self.holder);outer.addWidget(self.scroll,1)
  line=QFrame();line.setObjectName('divider');outer.addWidget(line)
  footer=QHBoxLayout();footer.setSpacing(4)
  for label,method in [('Completed',self.completed_tasks),('History',self.history),('Settings',self.settings)]:
   b=QPushButton(label);b.setObjectName('footer');b.setFixedHeight(27);b.clicked.connect(method);footer.addWidget(b)
  outer.addLayout(footer)
 def make_tray(self):
  pix=QPixmap(32,32);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setBrush(QColor('#26b6a8'));p.setPen(Qt.NoPen);p.drawRoundedRect(2,2,28,28,7,7);p.setPen(QColor('white'));p.drawText(pix.rect(),Qt.AlignCenter,'✓');p.end()
  self.tray=QSystemTrayIcon(QIcon(pix),self);menu=QMenu();show=menu.addAction('Show HelloTasks');show.triggered.connect(self.focus_entry);add=menu.addAction('Add task');add.triggered.connect(self.focus_entry);menu.addSeparator();quit_action=menu.addAction('Quit');quit_action.triggered.connect(self.quit_app);self.tray.setContextMenu(menu);self.tray.activated.connect(lambda reason:self.focus_entry() if reason==QSystemTrayIcon.DoubleClick else None)
  if QSystemTrayIcon.isSystemTrayAvailable():self.tray.show()
 def configure_hotkey(self):
  try:
   import keyboard
   keyboard.unhook_all_hotkeys()
   if self.store.get('hotkey',True):keyboard.add_hotkey('ctrl+alt+space',lambda:self.bridge.focus.emit());self.hotkey_registered=True
  except Exception as e:
   self.hotkey_registered=False
   print('Global hotkey unavailable:',e)
 def show_main(self):self.mini_widget.hide();self.showNormal();self.raise_();self.activateWindow()
 def focus_entry(self):self.show_main();self.open_add_dialog()
 def open_add_dialog(self):
  dlg=TaskDialog(self)
  if dlg.exec():
   title,tag,note=dlg.values();self.store.add(title,tag,note=note);self.refresh()
 def add_task(self):self.open_add_dialog()
 def clear_layout(self,layout):
  while layout.count():
   item=layout.takeAt(0)
   if item.widget():item.widget().deleteLater()
   elif item.layout():self.clear_layout(item.layout())
 def view_details(self,task_id):
  rows=self.store.rows('SELECT * FROM tasks WHERE id=?',(task_id,))
  if not rows:return
  task=rows[0]
  dlg=QDialog(self);dlg.setWindowTitle('Task details — HelloTasks');dlg.setMinimumWidth(330)
  lay=QVBoxLayout(dlg);lay.setContentsMargins(18,18,18,16);lay.setSpacing(10)
  title=QLabel(task['title']);title.setObjectName('taskTitle');title.setWordWrap(True);lay.addWidget(title)
  tag=QLabel('#'+(task['tag'] or 'Untagged'));tag.setObjectName('tagChip');lay.addWidget(tag,0,Qt.AlignLeft)
  lay.addWidget(QLabel('NOTE'))
  note=QLabel(task['note'] or 'No note added.');note.setWordWrap(True);note.setTextInteractionFlags(Qt.TextSelectableByMouse);lay.addWidget(note)
  info=QLabel('Status: '+('Completed' if task['done'] else 'Active')+'\nCreated: '+str(task['created']).replace('T',' '))
  info.setObjectName('muted');lay.addWidget(info)
  controls=QHBoxLayout()
  edit=QPushButton('Edit');close=QPushButton('Close')
  controls.addWidget(edit);controls.addWidget(close);lay.addLayout(controls)
  close.clicked.connect(dlg.accept)
  def edit_task():
   editor=TaskDialog(dlg,task)
   if editor.exec():
    title,tag,note=editor.values()
    self.store.run('UPDATE tasks SET title=?,tag=?,note=? WHERE id=?',(title,tag,note,task_id))
    dlg.accept();self.refresh()
  edit.clicked.connect(edit_task)
  dlg.exec()
 def task_widget(self,task):
  frame=QFrame();frame.setObjectName('task');frame.setProperty('done','true' if task['done'] else 'false')
  v=QVBoxLayout(frame);v.setContentsMargins(8,6,7,6);v.setSpacing(2)
  row=QHBoxLayout();row.setSpacing(6)
  cb=QCheckBox();cb.setToolTip('Mark completed' if not task['done'] else 'Restore task')
  cb.setChecked(bool(task['done']));cb.toggled.connect(lambda checked,tid=task['id']:self.toggle(tid,checked));row.addWidget(cb)
  title=QPushButton(task['title']);title.setObjectName('taskLink');title.setToolTip('View task details')
  title.setStyleSheet('text-align:left;background:transparent;border:0;padding:0;font-size:12px;font-weight:600;'+('color:#94a3b8;text-decoration:line-through;' if task['done'] else ''))
  title.clicked.connect(lambda checked=False,tid=task['id']:self.view_details(tid));row.addWidget(title,1)
  more=QPushButton('⋯');more.setObjectName('iconButton');more.setFixedSize(23,22)
  more.setToolTip('Task options');more.clicked.connect(lambda checked=False,t=task,b=more:self.task_menu(t,b));row.addWidget(more)
  v.addLayout(row)
  if task['tag'] and task['tag']!='Untagged':
   metadata=QHBoxLayout();metadata.setContentsMargins(24,0,0,0)
   chip=QLabel('#'+task['tag']);chip.setObjectName('tagChip');metadata.addWidget(chip,0);metadata.addStretch();v.addLayout(metadata)
  return frame
 def refresh(self):
  selected=self.tag_filter.currentText();tags=['All tags']+[r['tag'] for r in self.store.rows('SELECT DISTINCT tag FROM tasks ORDER BY tag')]
  self.tag_filter.blockSignals(True);self.tag_filter.clear();self.tag_filter.addItems(tags);self.tag_filter.setCurrentText(selected if selected in tags else 'All tags');self.tag_filter.blockSignals(False)
  self.refresh_tasks()
 def refresh_tasks(self):
  tag=self.tag_filter.currentText();status=self.status_filter.currentText()
  rows=self.store.rows('SELECT * FROM tasks ORDER BY done ASC,id DESC')
  rows=[r for r in rows if (tag in ('','All tags') or r['tag']==tag) and not r['done']]  # Main view always shows active tasks only
  self.clear_layout(self.tasks_layout)
  if not rows:
   empty=QLabel('Nothing here yet.\nAdd a task to get started.' if status!='Completed' else 'No completed tasks yet.')
   empty.setObjectName('muted');empty.setAlignment(Qt.AlignCenter);empty.setMinimumHeight(130);self.tasks_layout.addWidget(empty)
  for r in rows:self.tasks_layout.addWidget(self.task_widget(r))
  self.tasks_layout.addStretch()
  active_count=self.store.rows('SELECT COUNT(*) AS n FROM tasks WHERE done=0')[0]['n']
  self.count.setText(f'{active_count} active')
  self.section.setText('YOUR TASKS')
  if hasattr(self,'mini_widget') and self.mini_widget.isVisible():self.mini_widget.update_tasks()
 def toggle(self,task_id,done):self.store.complete(task_id,done);self.refresh()
 def task_menu(self,task,button):
  m=QMenu(self);details=m.addAction('View details');edit=m.addAction('Edit task');change=m.addAction('Change tag');delete=m.addAction('Delete task');action=m.exec(button.mapToGlobal(button.rect().bottomLeft()))
  if action==details:self.view_details(task['id'])
  elif action==delete:self.store.run('DELETE FROM tasks WHERE id=?',(task['id'],));self.refresh()
  elif action==edit:
   dlg=TaskDialog(self,task)
   if dlg.exec():
    title,tag,note=dlg.values();self.store.run('UPDATE tasks SET title=?,tag=?,note=? WHERE id=?',(title,tag,note,task['id']));self.refresh()
  elif action==change:
   val,ok=QInputDialog.getText(self,'Change tag','Tag:',text=task['tag'])
   if ok:self.store.run('UPDATE tasks SET tag=? WHERE id=?',(val.strip().lstrip('#') or 'Untagged',task['id']));self.refresh()
 def completed_tasks(self):
  # Completed tasks live in a dedicated window, not the active-task list.
  dlg=QDialog(self);dlg.setWindowTitle('Completed Tasks — HelloTasks');dlg.resize(390,440)
  lay=QVBoxLayout(dlg);lay.setContentsMargins(14,14,14,12);lay.setSpacing(8)
  heading=QLabel('Completed Tasks');heading.setObjectName('heading');lay.addWidget(heading)
  hint=QLabel('Finished tasks are saved here. Restore any task to make it active again.')
  hint.setObjectName('muted');hint.setWordWrap(True);lay.addWidget(hint)
  scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
  holder=QWidget();items=QVBoxLayout(holder);items.setContentsMargins(2,2,2,2);items.setSpacing(6)
  completed=self.store.rows('SELECT * FROM tasks WHERE done=1 ORDER BY completed DESC,id DESC')
  if not completed:
   empty=QLabel('No completed tasks yet.');empty.setObjectName('muted');empty.setAlignment(Qt.AlignCenter)
   items.addWidget(empty)
  for task in completed:
   card=QFrame();card.setObjectName('task');line=QHBoxLayout(card);line.setContentsMargins(9,7,9,7);line.setSpacing(6)
   label=QPushButton(task['title']);label.setObjectName('taskLink');label.setToolTip('View task details')
   label.setStyleSheet('text-align:left;background:transparent;border:0;padding:0;font-size:12px;font-weight:600;')
   label.clicked.connect(lambda checked=False,tid=task['id']:self.view_details(tid));line.addWidget(label,1)
   restore=QPushButton('Restore');restore.setToolTip('Move back to active tasks');restore.setObjectName('restoreButton');restore.setMinimumSize(82,32);restore.setSizePolicy(restore.sizePolicy().Policy.Fixed,restore.sizePolicy().Policy.Fixed)
   def restore_task(checked=False,tid=task['id']):
    self.store.complete(tid,False);self.refresh();dlg.accept();self.completed_tasks()
   restore.clicked.connect(restore_task);line.addWidget(restore)
   items.addWidget(card)
  items.addStretch();scroll.setWidget(holder);lay.addWidget(scroll,1)
  close=QPushButton('Close');close.clicked.connect(dlg.accept);lay.addWidget(close)
  dlg.exec()
 def history(self):
  dlg=QDialog(self);dlg.setWindowTitle('Task History');dlg.resize(420,400);lay=QVBoxLayout(dlg);lst=QListWidget()
  for r in self.store.rows('SELECT * FROM history ORDER BY id DESC LIMIT 500'):lst.addItem(f"{r['completed'][:16]}  ✓  {r['title']}  #{r['tag']}")
  lay.addWidget(lst);rec=QLabel('Recent 500 completion events (stored locally).');rec.setObjectName('muted');lay.addWidget(rec);dlg.exec()
 def settings(self):
  dlg=SettingsDialog(self.store,self)
  if dlg.exec():
   self.apply_top();self.setStyleSheet(self.theme_style());self.mini_widget.setStyleSheet(self.theme_style());self.show();self.configure_hotkey();self.update_startup();self.refresh()
 def update_startup(self):
  if sys.platform!='win32':return
  try:
   import winreg
   with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run',0,winreg.KEY_SET_VALUE) as key:
    if self.store.get('startup',False):
     exe=sys.executable
     cmd=f'"{exe}"' if getattr(sys,'frozen',False) else f'"{exe}" "{Path(__file__).resolve()}"'
     winreg.SetValueEx(key,APP,0,winreg.REG_SZ,cmd)
    else:
     try:winreg.DeleteValue(key,APP)
     except FileNotFoundError:pass
  except OSError as e:QMessageBox.warning(self,'Startup setting',str(e))
 def changeEvent(self,event):
  super().changeEvent(event)
  if event.type()==event.Type.WindowStateChange and self.isMinimized():
   QTimer.singleShot(100,self.minimize_to_widget)
 def minimize_to_widget(self):
  if self.isMinimized():self.hide();self.mini_widget.show_near_taskbar()
 def closeEvent(self,event):
  if QSystemTrayIcon.isSystemTrayAvailable():event.ignore();self.hide();self.mini_widget.show_near_taskbar();self.tray.showMessage('HelloTasks','Tasks remain active until you check them off.',QSystemTrayIcon.Information,1500)
  else:event.accept()
 def quit_app(self):self.mini_widget.hide();self.tray.hide();QApplication.instance().quit()

def main():
 app=QApplication(sys.argv);app.setQuitOnLastWindowClosed(False);window=Main();window.show();sys.exit(app.exec())
if __name__=='__main__':main()
