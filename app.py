import string
import csv

from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, g
from flask_session import Session
from helpers import currentmonth, currentyear, monthdays, hashit, wochentag, rand, apology, login_required, nextmonth
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash



# configure application
app = Flask(__name__)

# connect to budio6.db
db = SQL("sqlite:///budio6.db")
db.execute("PRAGMA foreign_keys = ON;")

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

"""some global variables"""
# current team                                                        #### I think this never updates!!!!
team = db.execute("SELECT * FROM users ORDER BY handle;")

# initialize common Abwesenheits-Dict
abw = {}

# initialize Abwesenheits-Dict per person
for person in team:
    abw[person['handle']] = {}

# list with all Abwesenheits-db
all_abw_lsts = []

# list with all schedules
alle_dienstpläne = []

# Minutensätze
RBS_live = 2.26
contraacht_live = 2.98
BCF_live = 170
RBS_vp = 2.75
aut_live = 2.98
Hallo_live = 2.98
andere_live = 2.98
""""""

@app.route('/')
@login_required
def index():
    """Kommende Dienste/fehlende Minuten"""
    try:
        sendungen = db.execute("SELECT * FROM ? WHERE Besetzung LIKE ? OR Besetzung LIKE ? OR Besetzung LIKE ?;", f"sendungen_{currentmonth()}", session["user_handle"], f'{session["user_handle"]}+%', f'%+{session["user_handle"]}')
        return render_template("index.html", sendungen=sendungen)
    except:
        return render_template("index.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Bitte Usernamen eingeben", code=400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Bitte Passwort eingeben", code=400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE name = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["pw_hash"], request.form.get("password")):
            return apology("Username oder Passwort ungültig", code=400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["user_name"] = rows[0]["name"]
        session["user_handle"] = rows[0]["handle"]
        session["admin"] = rows[0]["admin"] == 'True'

        # Redirect user to home page
        return redirect("/")

    return render_template('login.html', methods=["GET", "POST"])

@app.route('/register', methods=["GET", "POST"])
def register():

    if request.method == "POST":

         # get input from form
        name = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # check if password is has at least one lower case letter, one upper case letter and one of these: !§$%&?
        lowcse = 0
        upcse = 0
        spec = 0
        lw = string.ascii_lowercase
        up = string.ascii_uppercase
        for i in password:
            if i in lw:
                lowcse = 1
            if i in up:
                upcse = 1
            if i in ['!', '§', '$', '%', '&', '?', '#']:
                spec = 1

        # render apology if name is blank
        if not db.execute("SELECT name FROM users WHERE name LIKE ?;", name):
            return apology('Keine Berechtigung', code=400)

        # render apology if name already exists
        elif not db.execute("SELECT pw_hash FROM users WHERE name = ?;", name):
            return apology('User bereits registriert', code=400)

        # render apology if password is no good
        elif lowcse == 0 or upcse == 0 or spec == 0:
            return apology('1 Kleinbuchstabe, 1 Großbuchstabe und ein Sonerzeichen (!, §, $, %, &, ?, #)', code=400)

        # render apology if no password or confirmation wrong
        elif not password or password != confirmation:
            return apology('Passwort/Bestätigung ungültig', code=400)

        # generate password hash and insert new user to the database
        else:
            pw_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            db.execute("UPDATE users SET pw_hash = ? WHERE name LIKE ?;", pw_hash, name)

        return redirect('/login')

    else:
        return render_template("register.html")

@app.route('/abwesenheiten', methods=["GET", "POST"])
@login_required
def abwesenheiten():
    """Abwesenheitsliste"""

    # initialize tablename
    now = datetime.now()
    tablename = 'abw_' + str(now.year) + '_' + str(now.month + 1).zfill(2)

    # create or open table abwesenheiten_{month} in db
    if not db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?;", tablename):
        db.execute("CREATE TABLE ? (user_id INTEGER NOT NULL PRIMARY KEY, handle TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE);", tablename)
        for d in range(monthdays(datetime.now().month + 1)):
            db.execute("ALTER TABLE ? ADD COLUMN ? TEXT;", tablename, 'day ' + str(d))
        for person in team:
            db.execute("INSERT INTO ? (handle) VALUES (?);", tablename, person['handle'])
        if tablename not in all_abw_lsts:
            all_abw_lsts.append(tablename) 

    # current month as str
    current_month = currentmonth()
    # next month as str
    next_month = nextmonth()
    # number of days in current month
    daynum = monthdays(datetime.now().month + 1)

    # import data from abwesenheiten_{month}
    alles = db.execute("SELECT * FROM ?;", tablename)
    count = 0
    for person_dict in alles:
        for day in range(daynum):
            abw[person_dict['handle']][day] = person_dict['day ' + str(day)]

    # if user gets there via post
    if request.method == "POST":
        
        # loop through every table cell and get input and/or changes
        # if non-admin user update only user cells
        if session["admin"] == False:    
            for person in team:
                if person['handle'] == session["user_handle"]:
                    for day in range(daynum):
                        i = day + (person['id'] * daynum) - daynum
                        old_inp = db.execute('SELECT ? FROM ? WHERE handle LIKE ?;', 'day ' + str(day), tablename, person['handle'])
                        input = request.form.get(f"{i}")

                        # if input changed, update db and abw-dict
                        if input != old_inp:
                            abw[i] = input
                            abw[person['handle']][day] = input
                            db.execute('UPDATE ? SET ? = ? WHERE handle LIKE ?;', tablename, 'day ' + str(day), input, person['handle'])

                        try:
                            if abw[i].strip() == '':
                                del abw[i]
                        except:
                            continue
        # if admin user update whole table
        else:
            for person in team:
                for day in range(daynum):
                    i = day + (person['id'] * daynum) - daynum
                    old_inp = db.execute('SELECT ? FROM ? WHERE handle LIKE ?;', 'day ' + str(day), tablename, person['handle'])
                    input = request.form.get(f"{i}")

                    # if input changed, update db and abw-dict
                    if input != old_inp:
                        abw[i] = input
                        abw[person['handle']][day] = input
                        db.execute('UPDATE ? SET ? = ? WHERE handle LIKE ?;', tablename, 'day ' + str(day), input, person['handle'])

                    try:
                        if abw[i].strip() == '':
                            del abw[i]
                    except:
                        continue

        return render_template("abwesenheiten.html", current_month=current_month, team=team, daynum=daynum, abw=abw, next_month=next_month)
    
    else:
        return render_template("abwesenheiten.html", current_month=current_month, team=team, daynum=daynum, abw=abw, next_month=next_month)


@app.route('/dienstplan', methods=["GET", "POST"])
@login_required
def dienstplan():
    """Sendungen aus Datei einlesen und ausgeben"""
    
    # current month
    current_month = currentmonth()

    if request.form.get("import") is not None:
    # ask user for filename
        imp = True
        return render_template("dienstplan.html", imp=imp)
    
    if request.form.get("import_file") is not None:
        filename = request.form.get("import_file")
        sendungen = [] 
        try:
            with open(filename, encoding='utf-16') as csv_file:
                handle = csv.DictReader(csv_file, delimiter=',')
                for line in handle:
                    sendungen.append(line)

        except:
            imp = True
            flash('Datei nicht gefunden!')
            return render_template("dienstplan.html", imp=True)
        
         # check if sendungen table exists and create it if not
        if not db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?;", f"sendungen_{current_month}"):
            db.execute("""CREATE TABLE ? 
                (id INTEGER NOT NULL PRIMARY KEY UNIQUE, Datum TEXT NOT NULL, Zeit TEXT, Min INTEGER, 
                Titel TEXT, Besetzung TEXT, Ort TEXT, Region TEXT, 
                Programm TEXT, Live TEXT, Redakteur TEXT, DERNummer TEXT, Hash TEXT);""", f"sendungen_{current_month}")
            for sendung in sendungen:
                db.execute("""INSERT INTO ? (Datum, Zeit, Min, Titel, Ort, Region, Programm, Live, Redakteur, DERNummer) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""", f"sendungen_{current_month}", sendung['Datum'], sendung['Zeit'], sendung['Min'], sendung['Titel'], sendung['Ort'], sendung['Region'], sendung['Programm'], sendung['Live'], sendung['Redakteur'], sendung['DERNummer'])

        return render_template("dienstplan.html", imp=False, sendungen=sendungen)

    # delete everything
    if request.form.get("delete") is not None:
        try:
            db.execute("DROP TABLE ?;", f"sendungen_{current_month}")
        except:
            pass
        try:    
            db.execute("DROP TABLE ?;", f"sendungen_{current_month}_final")
        except:
            pass
        return render_template("dienstplan.html", imp=True)

    # create schedule
    if request.form.get("make_schedule") is not None:

        # create table for best version
        if not db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?;", f"sendungen_{current_month}_final"):
            db.execute("""CREATE TABLE ? 
                (id INTEGER NOT NULL PRIMARY KEY UNIQUE, Datum TEXT NOT NULL, Zeit TEXT, Min INTEGER, 
                Titel TEXT, Besetzung TEXT, Ort TEXT, Region TEXT, 
                Programm TEXT, Live TEXT, Redakteur TEXT, DERNummer TEXT, Hash TEXT);""", f"sendungen_{current_month}_final")

        # delete old best schedule
        try:
            db.execute("UPDATE ? SET Besetzung = null WHERE Besetzung NOT null;", f"sendungen_{current_month}_final")
        except:
            pass

        # initialiaze deviation comparison variable
        absolute_final = 0

        # date ending ".03.2023"
        ending = f".{datetime.now().month:02d}.{datetime.now().year}"

        # find current abw-table
        current_abw = f"abw_{datetime.now().year}_{datetime.now().month:02d}"

        # create multiple versions
        for i in range(10):

            # delete old schedule
            db.execute("UPDATE ? SET Besetzung = null WHERE Besetzung NOT null;", f"sendungen_{current_month}")

            # distribute shows to team
            for day in range(monthdays(datetime.now().month)):

                # find all available persons
                available_persons = db.execute(f'SELECT handle FROM ? WHERE ("day {day}" NOT LIKE "x" AND handle NOT IN (SELECT Besetzung FROM ? WHERE Datum LIKE ? AND Besetzung IS NOT null GROUP BY Besetzung));', current_abw, f"sendungen_{current_month}", f"{day+1:02d}.{datetime.now().month:02d}.{datetime.now().year}")

                # RBS Aktuell BL1
                try:
                    db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                    WHERE (Titel LIKE 'RBS Aktuell Bundesland 1%' OR Titel LIKE 'Bundesland 1 Wetter' OR Titel LIKE 'RBS Sport' OR Titel LIKE 'Sportschau - Die Bundesliga am Sonntag') 
                    AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ ending)
                except:
                    pass

                # RBS Aktuell BL2
                try:
                    db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                    WHERE (Titel LIKE 'RBS Aktuell Bundesland 2%' OR Titel LIKE 'Bundesland 2 Wetter') 
                    AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ending)
                except:
                    pass

                # Buffet + KoT + HalloTV
                if wochentag(f"{day+1:02d}"+ending) in [0, 1, 2, 3, 4]:
                    try:
                        db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                        WHERE (Titel LIKE 'DER-Buffet' OR (Titel LIKE 'KaOTe' AND Zeit LIKE '16%')  OR Titel LIKE 'Hallo TV Nachrichten AT')
                        AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ending)
                    except:
                        pass

                    # KoT + Bundesland8 heute
                    try:
                        db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                        WHERE ((Titel LIKE 'KaOTe' AND Zeit LIKE '17%') OR Titel LIKE 'Bundesland8 heute')
                        AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ending)
                    except:
                        pass

                # if Sonntag BL1
                if db.execute("SELECT * FROM ? WHERE (Titel LIKE 'Sonntag BL1' AND Datum Like ?)", f"sendungen_{current_month}", f"{day+1:02d}"+ending):
                    try:
                        db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                        WHERE (Titel LIKE 'Sonntag BL1' OR Titel LIKE 'Bundesland8 heute')
                        AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ending)
                    except:
                        pass

                # if Sonntag BL2
                if db.execute('SELECT * FROM ? WHERE (Titel LIKE "Sonntag BL2" AND Datum Like ?)', f"sendungen_{current_month}", f"{day+1:02d}"+ending):
                    try:
                        db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                        WHERE (Titel LIKE 'Sonntag BL2' OR Titel LIKE 'Hallo TV Nachrichten AT')
                        AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ending)
                    except:
                        pass

                # if kein Sonntag BL2, dann HalloTV mit Nachrichten BL2 oder Sonntag BL1
                if wochentag(f"{day+1:02d}"+ending) == 6 and not db.execute("""SELECT * FROM ? WHERE Titel LIKE 'Sonntag BL2' AND Datum LIKE ?;""", f"sendungen_{current_month}", f"{day+1:02d}"+ending):
                    try:
                        db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                        WHERE (Titel LIKE 'Sonntag BL1' OR Titel LIKE 'Bundesland8 heute' OR Titel LIKE 'Hallo TV Nachrichten AT')
                        AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ending)
                    except:
                        pass
                
                # Report Mainz, Addsub
                if db.execute('SELECT * FROM ? WHERE ((Titel LIKE "Report Mainz" OR Titel LIKE "Addsub") AND Datum LIKE ?);', f"sendungen_{current_month}", f"{day+1:02d}"+ending):
                    try:
                        db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                        WHERE (Titel LIKE 'LS Bundesland 2' OR Titel LIKE 'Report Mainz' OR Titel LIKE 'Addsub')
                        AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ending)
                    except:
                        pass

                # TEC, Fußball live
                if (db.execute("""SELECT * FROM ? 
                                WHERE (Titel LIKE 'Kinder Club' AND Datum LIKE ?);""", f"sendungen_{current_month}", f"{day+1:02d}"+ending)) and (db.execute("""SELECT * FROM ? 
                                WHERE (Titel LIKE 'RBS SPORT: %' AND Datum LIKE ?);""", f"sendungen_{current_month}", f"{day+1:02d}"+ending)):
                    try:
                        db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                        WHERE (Titel LIKE 'Kinder Club' OR Titel LIKE 'RBS Sport: %')
                        AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ending)
                    except:
                        pass
                
                # RBS Sport Fußball live, RBS Sport am Samstag 
                if (db.execute("""SELECT * FROM ? 
                                WHERE (Titel LIKE "RBS SPORT: %" AND Datum LIKE ?);""", f"sendungen_{current_month}", f"{day+1:02d}"+ending)) and (db.execute("""SELECT * FROM ? 
                                WHERE (Titel LIKE "RBS SPORT" AND Datum LIKE ?);""", f"sendungen_{current_month}", f"{day+1:02d}"+ending)):
                    try:
                        db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                        WHERE (Titel LIKE 'RBS Sport: %' OR Titel LIKE 'RBS Sport')
                        AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ending)
                    except:
                        pass

                # RBS Sport am Samstag, Bundesland8 heute und Hallo TV 
                if (db.execute("""SELECT * FROM ? 
                                WHERE (Titel LIKE "RBS SPORT" AND Datum LIKE ?);""", f"sendungen_{current_month}", f"{day+1:02d}"+ending)) and (db.execute("""SELECT * FROM ? 
                                WHERE (Titel LIKE "Bundesland8 heute" AND Datum LIKE ?);""", f"sendungen_{current_month}", f"{day+1:02d}"+ending)) and (db.execute("""SELECT * FROM ? 
                                WHERE (Titel LIKE "Hallo TV Nachrichten AT" AND Datum LIKE ?);""", f"sendungen_{current_month}", f"{day+1:02d}"+ending)) and wochentag(f"{day+1:02d}"+ending) == 5:
                    try:
                        db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                        WHERE (Titel LIKE 'RBS Sport' OR Titel LIKE 'Bundesland8 heute' OR Titel LIKE 'Hallo TV Nachrichten AT')
                        AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), f"{day+1:02d}"+ending)
                    except:
                        pass
                
                # restliche Sendungen > 60 Minuten
                for sendung in db.execute('SELECT * FROM ? WHERE Besetzung IS null AND Datum LIKE ?;', f"sendungen_{current_month}", f"{day+1:02d}"+ending):
                    try:
                        if sendung['Min'] > 60 or sendung['Programm'] == 'BCF':
                            try:
                                db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                                WHERE Titel LIKE ? 
                                AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons) + '+' + rand(available_persons), hashit(), sendung['Titel'], f"{day+1:02d}"+ending)
                            except:
                                pass
                    except:
                        pass
                
                # restliche Sendungen
                for sendung in db.execute('SELECT * FROM ? WHERE Besetzung IS null AND Datum LIKE ?;', f"sendungen_{current_month}", f"{day+1:02d}"+ending):
                    try:
                        db.execute("""UPDATE ? SET Besetzung = ?, Hash = ? 
                        WHERE Titel LIKE ? 
                        AND Datum LIKE ?;""", f"sendungen_{current_month}", rand(available_persons), hashit(), sendung['Titel'], f"{day+1:02d}"+ending)
                    except:
                        pass
        
            # set default minutes for Bundesland8 heute and HalloTV
            for sendung in db.execute("SELECT * FROM ? WHERE Titel LIKE 'Bundesland8 heute'", f"sendungen_{currentmonth()}"):
                if wochentag(sendung['Datum']) == 6:
                    db.execute("UPDATE ? SET Min = 13 WHERE Titel LIKE 'Bundesland8 heute' AND Datum LIKE ?", f"sendungen_{currentmonth()}", sendung['Datum'])
                else:
                    db.execute("UPDATE ? SET Min = 21 WHERE Titel LIKE 'Bundesland8 heute' AND Datum LIKE ?", f"sendungen_{currentmonth()}", sendung['Datum'])

            for sendung in db.execute("SELECT * FROM ? WHERE Titel LIKE 'Hallo TV Nachrichten AT'", f"sendungen_{currentmonth()}"):
                if wochentag(sendung['Datum']) == 5:
                    db.execute("UPDATE ? SET Min = 8 WHERE Titel LIKE 'Hallo TV Nachrichten AT' AND Datum LIKE ?", f"sendungen_{currentmonth()}", sendung['Datum'])
                else:
                    db.execute("UPDATE ? SET Min = 15 WHERE Titel LIKE 'Hallo TV Nachrichten AT' AND Datum LIKE ?", f"sendungen_{currentmonth()}", sendung['Datum'])

            # choose best version
            dienste = {}
            absolute_current = 0
            for person in team:
                count = db.execute("SELECT *, COUNT(DISTINCT hash), SUM(Min) FROM ? WHERE Besetzung LIKE ? OR Besetzung LIKE ? OR Besetzung LIKE ?;", f"sendungen_{current_month}", person['handle'], f"{person['handle']}+%", f"%+{person['handle']}")
                dienste[person['handle']] = count[0]['COUNT(DISTINCT hash)']
                absolute_current += abs(dienste[person['handle']] - int(person['workload'] / 7 * monthdays(datetime.now().month)))
            if absolute_final == 0 or absolute_current < absolute_final:
                absolute_final = absolute_current
                db.execute("DELETE FROM ?;", f"sendungen_{current_month}_final")
                db.execute("INSERT INTO ? SELECT * FROM ?;", f"sendungen_{current_month}_final", f"sendungen_{current_month}")
            print(absolute_current)


    try:
        return render_template("dienstplan.html", sendungen=db.execute("SELECT * FROM ?;", f"sendungen_{current_month}_final"), current_month=current_month, team=team)

    except:
        try:
            return render_template("dienstplan.html", sendungen=db.execute("SELECT * FROM ?;", f"sendungen_{current_month}"))
        except:
            return render_template("dienstplan.html", imp=True)

@app.route('/stats')
@login_required
def stats():
    dienste = {}
    min_per_day = {}
    absolute = 0
    team = db.execute("SELECT * FROM users ORDER BY handle;")
    current_month = currentmonth()
    try:
        for person in team:
            count = db.execute("SELECT *, COUNT(DISTINCT hash), SUM(Min) FROM ? WHERE Besetzung LIKE ? OR Besetzung LIKE ? OR Besetzung LIKE ?;", f"sendungen_{current_month}_final", person['handle'], f"{person['handle']}+%", f"%+{person['handle']}")
            dienste[person['handle']] = count[0]['COUNT(DISTINCT hash)']
            absolute += abs(dienste[person['handle']] - int(person['workload'] / 7 * monthdays(datetime.now().month)))
            try:
                min_per_day[person['handle']] = int(count[0]['SUM(Min)'] / count[0]['COUNT(DISTINCT hash)'])
            except:
                pass
        dienste['total'] = db.execute("SELECT COUNT(DISTINCT hash) FROM ?", f"sendungen_{current_month}_final")[0]['COUNT(DISTINCT hash)']
        dienste['gewollt'] = db.execute("SELECT SUM(workload) FROM users;")[0]['SUM(workload)'] / 7 * monthdays(datetime.now().month)
    except:
        return redirect("/")
    return render_template("stats.html", team=team, sendungen=db.execute("SELECT * FROM ?;", f"sendungen_{current_month}_final"), dienste=dienste, min_per_day=min_per_day, absolute=absolute, daynum=monthdays(datetime.now().month))


@app.route('/team', methods=["GET", "POST"])
@login_required
def teamseite():
    team = db.execute("SELECT * FROM users ORDER BY handle;")
    if request.method == "POST":

        # buttons delete user/add user:
        if request.form.get('new-user') is not None:
            return redirect("/newuser")
        for person in team:
            if request.form.get(f"{person['handle']}_update") is not None:
                db.execute("UPDATE users SET usr_update = ? WHERE handle LIKE ?;", 'True', person['handle'])
                return redirect("/update_user")

            if request.form.get(f"{person['handle']}_delete") is not None:
                db.execute("DELETE FROM users WHERE handle LIKE ?;", person['handle'])
                team = db.execute("SELECT * FROM users ORDER BY handle;")
                return render_template("team.html", team=team)
        
    else:
        return render_template("team.html", team=team)


@app.route('/logout', methods=["GET", "POST"])
@login_required
def logout():
    
    if request.method == "POST":
        if request.form.get('yes') is not None:
            session.clear()
            return '<h1>This was CS50!</h1>'
        
        if request.form.get('no') is not None:
            return redirect("/")

    else:
        return render_template("logout.html")


@app.route('/update_user', methods=["GET", "POST"])
@login_required
def update_user():
    team = db.execute("SELECT * FROM users ORDER BY handle;")
    if request.method == "POST":
        for person in team:
            if request.form.get(f"{person['handle']}_handle"):
                input = request.form.get(f"{person['handle']}_handle")
                try:
                    db.execute("UPDATE users SET handle = ? WHERE handle LIKE ?;", input, person['handle'])
                except:
                    return apology('Kürzel existiert bereits :(', code=400)
            if request.form.get(f"{person['handle']}_name"):
                input = request.form.get(f"{person['handle']}_name")
                db.execute("UPDATE users SET name = ? WHERE handle LIKE ?;", input, person['handle'])
            if request.form.get(f"{person['handle']}_workload"):
                input = request.form.get(f"{person['handle']}_workload")
                db.execute("UPDATE users SET workload = ? WHERE handle LIKE ?;", input, person['handle'])
            if request.form.get(f"{person['handle']}_telefonnummer"):
                input = request.form.get(f"{person['handle']}_telefonnummer")
                db.execute("UPDATE users SET telefonnummer = ? WHERE handle LIKE ?;", input, person['handle'])
            if request.form.get(f"{person['handle']}_admin") == 'on':
                db.execute("UPDATE users SET admin = 'True' WHERE handle Like ?;", person['handle'])
            if request.form.get(f"{person['handle']}_admin") != 'on' and person['admin'] == 'True' and person['usr_update'] == 'True':
                db.execute("UPDATE users SET admin = 'False' WHERE handle Like ?;", person['handle'])

            # set usr_update = False         
            db.execute("UPDATE users SET usr_update = 'False' WHERE handle LIKE ?;", person['handle'])
        
        return redirect("/team")
    
    else:
        return render_template("update_user.html", team=team)


@app.route('/newuser', methods = ["GET", "POST"])
def newuser():
    if request.method == "POST":
        if request.form.get("handle") and request.form.get("name"):
            handle = request.form.get("handle")
            try:
                db.execute("INSERT INTO users (handle, name) VALUES(?, ?);", handle, request.form.get("name"))
            except:
                return apology('Da ist was schiefgelaufen :( \n Kürzel und Name sind Pflichtfelder', code=400)
            if request.form.get("name"):
                input = request.form.get("name")
                db.execute("UPDATE users SET name = ? WHERE handle LIKE ?;", input, handle)
            if request.form.get("workload"):
                input = request.form.get("workload")
                db.execute("UPDATE users SET workload = ? WHERE handle LIKE ?;", input, handle)
            if request.form.get("telephone"):
                input = request.form.get()
                db.execute("UPDATE users SET telefonnummer = ? WHERE handle LIKE ?;", input, handle)
            if request.form.get("e-mail"):
                input = request.form.get()
                db.execute("UPDATE users SET email = ? WHERE handle LIKE ?;", input, handle)
        else:
            return apology('Kürzel und Name sind Pflichtfelder', code=400)

        return redirect("/team")

    else:
        return render_template("newuser.html")

