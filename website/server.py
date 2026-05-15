import hashlib
import json
import os
import re
import secrets
import sqlite3
import smtplib
import httpx
import urllib.parse
from email.message import EmailMessage
from datetime import date, timedelta, datetime
from pathlib import Path
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.requests import Request
import uvicorn
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR      = Path(__file__).parent
ROOT_DIR      = BASE_DIR.parent
FILES_DIR     = ROOT_DIR / "FILES"
CA_DIR        = FILES_DIR / "current-affairs"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR    = BASE_DIR / "static"
DB_PATH       = BASE_DIR / "users.db"

SECRET_KEY     = os.environ.get("SECRET_KEY", "dev-secret-groupsguru-2026")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "GroupsGuru@2026")

EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_PASS = os.environ.get("EMAIL_PASS", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---------------------------------------------------------------------------
# Auth — password helpers
# ---------------------------------------------------------------------------

def hash_password(pwd: str) -> str:
    salt = os.urandom(32)
    key  = hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt, 260_000)
    return salt.hex() + ":" + key.hex()


def verify_password(pwd: str, stored: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(":")
        key = hashlib.pbkdf2_hmac("sha256", pwd.encode(), bytes.fromhex(salt_hex), 260_000)
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Database — init + seed
# ---------------------------------------------------------------------------

def _seed_user(con, username: str, display_name: str, role: str, password: str) -> None:
    """Insert user only if username doesn't already exist."""
    row = con.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        con.execute(
            "INSERT INTO users (username, display_name, role, password_hash) VALUES (?,?,?,?)",
            (username, display_name, role, hash_password(password)),
        )
        con.commit()


def init_db() -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            display_name  TEXT NOT NULL,
            email         TEXT,
            password_hash TEXT NOT NULL,
            role          TEXT DEFAULT 'student',
            is_active     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS topic_progress (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            topic_id      TEXT NOT NULL,
            subject       TEXT NOT NULL,
            topic_title   TEXT,
            first_studied TEXT DEFAULT CURRENT_DATE,
            last_studied  TEXT DEFAULT CURRENT_DATE,
            study_count   INTEGER DEFAULT 1,
            minutes_spent INTEGER DEFAULT 0,
            UNIQUE(user_id, topic_id)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS revision_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            topic_id        TEXT NOT NULL,
            revision_number INTEGER NOT NULL,
            completed_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, topic_id, revision_number)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            token       TEXT PRIMARY KEY,
            user_id     INTEGER NOT NULL,
            expires_at  TEXT NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS topic_highlights (
            user_id         INTEGER NOT NULL,
            topic_id        TEXT NOT NULL,
            highlights_json TEXT DEFAULT '[]',
            updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, topic_id)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS topic_user_notes (
            user_id    INTEGER NOT NULL,
            topic_id   TEXT NOT NULL,
            content    TEXT DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, topic_id)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            topic_id   TEXT NOT NULL,
            front      TEXT NOT NULL,
            back       TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS mcqs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id       TEXT NOT NULL,
            question       TEXT NOT NULL,
            option_a       TEXT NOT NULL,
            option_b       TEXT NOT NULL,
            option_c       TEXT NOT NULL,
            option_d       TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            explanation    TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS paragraph_pins (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            topic_id   TEXT NOT NULL,
            para_index INTEGER NOT NULL,
            para_text  TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, topic_id, para_index)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS user_pomodoro_settings (
            user_id    INTEGER PRIMARY KEY,
            work_min   INTEGER DEFAULT 25,
            break_min  INTEGER DEFAULT 5,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS ca_reads (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ca_date TEXT NOT NULL,
            read_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, ca_date)
        )
    """)
    con.commit()

    # Admin — password overrideable via ADMIN_PASSWORD env var on Render
    _seed_user(con, "jayaramadmin", "Jayaram", "admin", os.environ.get("ADMIN_PASSWORD", "jayaramadmin@2026"))
    # Reserved student accounts
    _seed_user(con, "jayaram",   "Jayaram",   "student", "jayaram@2026")
    _seed_user(con, "leelarani", "Leela Rani","student", "leelarani@2026")
    _seed_user(con, "tejashree", "Tejashree", "student", "tejashree@2026")

    seed_mcqs(con)
    con.commit()
    con.close()


def seed_mcqs(con) -> None:
    """Populate sample MCQs for demonstration."""
    # Ancient India (Group 2 Screening)
    _q(con, "scr-hist-01", "Which of the following sites is NOT part of the Indus Valley Civilization?",
       "Harappa", "Mohenjo-daro", "Hastinapur", "Lothal",
       "C", "Hastinapur was an important site of the Vedic period, but not part of the primary Indus Valley Civilization sites like Harappa or Lothal.")
    
    _q(con, "scr-hist-01", "The 'Dockyard' of the Indus Valley Civilization was found at:",
       "Kalibangan", "Lothal", "Ropar", "Banawali",
       "B", "Lothal was the vital and only port city of the Indus Valley Civilization, featuring a massive brick basin that served as a dockyard.")

    # Logical Reasoning
    _q(con, "scr-ma-01", "In a certain code, 'APPLE' is written as 'BQQMF'. How is 'GRAPE' written?",
       "HSBQF", "HTAQF", "JSBQF", "HSARF",
       "A", "The logic is +1 for each letter. G+1=H, R+1=S, A+1=B, P+1=Q, E+1=F.")

    # Indian Society (Group 2 Screening)
    _q(con, "scr-soc-01", "Which of the following describes a kinship relationship based on blood ties?",
       "Affinal kinship", "Consanguineous kinship", "Fictive kinship", "Secondary kinship",
       "B", "Consanguineous kinship refers to relationships based on common blood or descent, such as parents and children.")
    
    _q(con, "scr-soc-01", "The practice where a woman has multiple husbands simultaneously is known as:",
       "Polygyny", "Polyandry", "Monogamy", "Endogamy",
       "B", "Polyandry is a form of polygamy where one woman is married to two or more men at the same time.")
    
    _q(con, "scr-soc-01", "Who introduced the concept of 'Sanskritization' to describe social mobility in the Indian caste system?",
       "B.R. Ambedkar", "M.N. Srinivas", "G.S. Ghurye", "Jyotirao Phule",
       "B", "M.N. Srinivas coined the term 'Sanskritization' to explain how lower castes emulate the rituals and practices of higher castes to improve their status.")
    
    _q(con, "scr-soc-01", "Which Constitutional Amendment provided 33% reservation for women in local bodies (Panchayats and Municipalities)?",
       "42nd & 44th Amendments", "73rd & 74th Amendments", "86th Amendment", "101st Amendment",
       "B", "The 73rd and 74th Constitutional Amendment Acts (1992) mandated 1/3rd (33%) reservation for women in local governance.")
    
    _q(con, "scr-soc-01", "Article 342 of the Indian Constitution empowers the President to notify which group?",
       "Scheduled Castes", "Scheduled Tribes", "Backward Classes", "Religious Minorities",
       "B", "Article 342 deals with the notification of Scheduled Tribes (STs) in India.")

    # Social Issues (scr-soc-02)
    _q(con, "scr-soc-02", "Under the POCSO Act (2012), at what age is an individual considered a child?",
       "Below 14 years", "Below 16 years", "Below 18 years", "Below 21 years",
       "C", "The Protection of Children from Sexual Offences (POCSO) Act defines a child as any person below the age of 18 years.")

    _q(con, "scr-soc-02", "Which Article of the Indian Constitution prohibits the employment of children below 14 years in factories or mines?",
       "Article 21", "Article 23", "Article 24", "Article 25",
       "C", "Article 24 specifically prohibits hazardous child labor for those under 14 years.")

    _q(con, "scr-soc-02", "The 'Mandal Commission' is associated with which of the following social issues?",
       "Communalism", "Regionalisation", "Caste and Reservation for OBCs", "Youth Unrest",
       "C", "The Mandal Commission (Socially and Educationally Backward Classes Commission) recommended 27% reservation for Other Backward Classes (OBCs).")

    # Welfare Mechanism (scr-soc-03)
    _q(con, "scr-soc-03", "Which Article of the Indian Constitution provides for the 'Abolition of Untouchability'?",
       "Article 14", "Article 15", "Article 16", "Article 17",
       "D", "Article 17 abolished 'Untouchability' and forbade its practice in any form.")

    _q(con, "scr-soc-03", "The PM-KISAN scheme provides income support of how much per year to farmer families?",
       "₹2,000", "₹4,000", "₹6,000", "₹10,000",
       "C", "PM-KISAN provides ₹6,000 per year in three equal installments.")

    _q(con, "scr-soc-03", "Which Constitutional Amendment established the National Commission for Backward Classes (Art 338B)?",
       "100th Amendment", "101st Amendment", "102nd Amendment", "103rd Amendment",
       "C", "The 102nd Constitutional Amendment Act of 2018 gave constitutional status to the NCBC.")

    _q(con, "scr-soc-03", "The MGNREGA Act (2005) guarantees how many days of wage employment in a financial year?",
       "100 days", "120 days", "150 days", "200 days",
       "A", "MGNREGA guarantees 100 days of unskilled manual work to every rural household.")

    # Constitution & Polity (pre-cp-01)
    _q(con, "pre-cp-01", "Which Act first introduced 'Separate Electorates' for Muslims in India?",
       "Indian Councils Act 1861", "Indian Councils Act 1892", "Indian Councils Act 1909", "Government of India Act 1919",
       "C", "The Indian Councils Act of 1909 (Morley-Minto Reforms) introduced communal representation by providing separate electorates for Muslims.")

    _q(con, "pre-cp-01", "Who moved the 'Objective Resolution' in the Constituent Assembly?",
       "Dr. B.R. Ambedkar", "Jawaharlal Nehru", "Sardar Patel", "Dr. Rajendra Prasad",
       "B", "Jawaharlal Nehru moved the Objective Resolution on December 13, 1946, which later became the Preamble of the Constitution.")

    _q(con, "pre-cp-01", "The concept of 'Directive Principles of State Policy' (DPSP) was borrowed from which Constitution?",
       "USA", "Ireland", "Canada", "UK",
       "B", "The DPSP in the Indian Constitution were inspired by the Irish Constitution.")

    _q(con, "pre-cp-01", "Which Amendment Act added the words 'Socialist, Secular and Integrity' to the Preamble?",
       "24th Amendment", "42nd Amendment", "44th Amendment", "52nd Amendment",
       "B", "The 42nd Constitutional Amendment Act (1976) is known as the 'Mini Constitution' and added these three words.")

    _q(con, "pre-cp-01", "The 'Regulating Act of 1773' designated the Governor of Bengal as the Governor-General of Bengal. Who was the first person to hold this office?",
       "Lord Clive", "Warren Hastings", "Lord Cornwallis", "Lord Wellesley",
       "B", "Warren Hastings became the first Governor-General of Bengal under the 1773 Act.")

    # Union & Federal Structure (pre-cp-02)
    _q(con, "pre-cp-02", "Under which Article can the Parliament of India admit or establish a new state that is NOT part of the existing Union?",
       "Article 1", "Article 2", "Article 3", "Article 4",
       "B", "Article 2 deals with the admission or establishment of new states that are not part of the Union of India.")

    _q(con, "pre-cp-02", "On what date was the separate Andhra State created, following the hunger strike of Potti Sreeramulu?",
       "August 15, 1947", "October 1, 1953", "November 1, 1956", "June 2, 2014",
       "B", "The separate Andhra State was formed on October 1, 1953, with Kurnool as its capital.")

    _q(con, "pre-cp-02", "Which Commission/Committee first rejected the linguistic basis for the reorganisation of states in 1948?",
       "Fazal Ali Commission", "Sarkaria Commission", "S.K. Dhar Commission", "Punchhi Commission",
       "C", "The S.K. Dhar Commission (1948) rejected the linguistic basis and recommended administrative convenience.")

    _q(con, "pre-cp-02", "The Indian Constitution is often described as 'Quasi-federal'. Who used this term?",
       "B.R. Ambedkar", "K.C. Wheare", "Granville Austin", "Ivor Jennings",
       "B", "Professor K.C. Wheare described the Indian Constitution as 'Quasi-federal' due to its unitary bias.")

    _q(con, "pre-cp-02", "The 7th Schedule of the Indian Constitution contains the three lists - Union, State, and Concurrent. In which list are 'Residuary Powers' kept in India?",
       "Union List", "State List", "Concurrent List", "None (Vested in Parliament)",
       "D", "In India, residuary powers are vested in the Union Parliament (consistent with a strong Centre).")

    # Governance & Authorities (pre-cp-03)
    _q(con, "pre-cp-03", "Article 74 of the Indian Constitution provides that there shall be a Council of Ministers headed by the Prime Minister to aid and advise whom?",
       "The Speaker", "The Chief Justice", "The President", "The Vice-President",
       "C", "The President of India exercises his functions on the aid and advice of the Council of Ministers.")

    _q(con, "pre-cp-03", "Who is the 'Constitutional Head' of a State in India?",
       "Chief Minister", "Governor", "Speaker of Assembly", "High Court Judge",
       "B", "The Governor is the constitutional/formal head of the state, while the CM is the real head.")

    _q(con, "pre-cp-03", "Which Constitutional Amendment Act introduced the 3-tier Panchayati Raj system in India?",
       "42nd Amendment", "44th Amendment", "73rd Amendment", "74th Amendment",
       "C", "The 73rd Constitutional Amendment Act (1992) gave constitutional status to Panchayati Raj Institutions.")

    _q(con, "pre-cp-03", "Who has the power to decide whether a bill is a 'Money Bill' or not?",
       "The President", "The Prime Minister", "The Speaker of Lok Sabha", "The Finance Minister",
       "C", "Under Article 110, the Speaker of the Lok Sabha has the final authority to decide if a bill is a Money Bill.")

    _q(con, "pre-cp-03", "How many members are nominated by the President to the Rajya Sabha for their excellence in science, art, literature, and social service?",
       "2", "10", "12", "15",
       "C", "The President nominates 12 members to the Rajya Sabha.")

    # LPG Impact & Regulatory Bodies (pre-cp-04)
    _q(con, "pre-cp-04", "Which committee recommended the introduction of the Goods and Services Tax (GST) in India?",
       "Vijay Kelkar Committee", "Rangarajan Committee", "Urjit Patel Committee", "Narasimham Committee",
       "A", "The Vijay Kelkar Committee (TF on Indirect Taxes) first recommended the introduction of a comprehensive GST in India.")

    _q(con, "pre-cp-04", "In which year did India adopt the New Economic Policy (LPG reforms) to tackle the balance of payments crisis?",
       "1985", "1991", "1995", "2000",
       "B", "The LPG (Liberalization, Privatization, and Globalization) reforms were introduced in 1991 by the Narasimha Rao government.")

    _q(con, "pre-cp-04", "Which of the following is a 'Quasi-judicial' body in India?",
       "NITI Aayog", "National Human Rights Commission", "Cabinet Committee on Security", "Parliamentary Accounts Committee",
       "B", "The NHRC has the powers of a civil court while investigating complaints of human rights violations, making it a quasi-judicial body.")

    _q(con, "pre-cp-04", "The Securities and Exchange Board of India (SEBI) was given statutory status in which year?",
       "1988", "1990", "1992", "1994",
       "C", "SEBI was established in 1988 but received statutory powers on January 30, 1992, through the SEBI Act, 1992.")

    _q(con, "pre-cp-04", "Under which Article of the Constitution is the Finance Commission of India constituted every five years?",
       "Article 260", "Article 270", "Article 280", "Article 290",
       "C", "Article 280 of the Constitution provides for a Finance Commission as a quasi-judicial body.")

    # Rights Issues (pre-cp-05)
    _q(con, "pre-cp-05", "The National Human Rights Commission (NHRC) was established under which legislation?",
       "Protection of Human Rights Act, 1993", "Civil Rights Act, 1955", "Human Rights Declaration, 1948", "Right to Information Act, 2005",
       "A", "The NHRC was established on October 12, 1993, under the Protection of Human Rights Ordinance, later replaced by the Act.")

    _q(con, "pre-cp-05", "Which Article of the Indian Constitution empowers the State to make 'special provisions for women and children'?",
       "Article 14", "Article 15(1)", "Article 15(3)", "Article 16",
       "C", "Article 15(3) is an exception to the rule of non-discrimination, allowing the State to make special provisions for women and children.")

    _q(con, "pre-cp-05", "In which year was the 'Protection of Children from Sexual Offences (POCSO) Act' enacted?",
       "2005", "2010", "2012", "2015",
       "C", "The POCSO Act was enacted in 2012 to protect children from sexual assault, harassment, and pornography.")

    _q(con, "pre-cp-05", "The 'Scheduled Castes and Scheduled Tribes (Prevention of Atrocities) Act' was passed in which year?",
       "1955", "1976", "1989", "2018",
       "C", "The Prevention of Atrocities (PoA) Act was enacted in 1989 to protect SC/ST individuals from social disability and atrocities.")

    _q(con, "pre-cp-05", "The National Commission for Scheduled Castes is established under which Article of the Constitution?",
       "Article 330", "Article 332", "Article 338", "Article 338A",
       "C", "Article 338 provides for the National Commission for Scheduled Castes, while 338A provides for the National Commission for STs.")


def _q(con, topic_id, q, a, b, c, d, correct, exp) -> None:
    """Helper to insert a question if it doesn't exist."""
    exist = con.execute("SELECT id FROM mcqs WHERE question = ?", (q,)).fetchone()
    if not exist:
        con.execute(
            "INSERT INTO mcqs (topic_id, question, option_a, option_b, option_c, option_d, correct_option, explanation) VALUES (?,?,?,?,?,?,?,?)",
            (topic_id, q, a, b, c, d, correct, exp)
        )


def db_get_user_by_username(username: str):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    con.close()
    return dict(row) if row else None


def db_get_user_by_email(email: str):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
    con.close()
    return dict(row) if row else None


def db_create_user(username: str, display_name: str, email: str, password: str) -> bool:
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO users (username, display_name, email, password_hash) VALUES (?,?,?,?)",
            (username, display_name, email or None, hash_password(password)),
        )
        con.commit()
        con.close()
        return True
    except sqlite3.IntegrityError:
        return False


def db_username_taken(username: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    con.close()
    return row is not None


def db_update_password(user_id: int, new_password: str) -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), user_id))
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# Session helper
# ---------------------------------------------------------------------------

def get_current_user(request: Request):
    uid = request.session.get("user_id")
    if not uid:
        return None
    return {
        "id":       uid,
        "username": request.session.get("username"),
        "role":     request.session.get("role"),
    }

# ---------------------------------------------------------------------------
# Group II — Official Syllabus Structure
# Source: APPSC Group II Syllabus PDF (5_PDFsam_APPSC_GROUP2_SYLLABUS.pdf)
# points = exact bullet points extracted from the official syllabus
# ---------------------------------------------------------------------------
G2_STRUCTURE = {
    "screening": {
        "label": "Screening Test",
        "subtitle": "General Studies & Mental Ability | 150 Marks | 150 Min",
        "sections": [
            {
                "title": "Indian History",
                "marks": 30,
                "topics": [
                    {
                        "id": "scr-hist-01",
                        "title": "Ancient India",
                        "points": [
                            "Salient features of Indus Valley Civilization and Vedic Age",
                            "Emergence of Buddhism and Jainism",
                            "Mauryan Empire and Gupta Empire: Their Administration, Socio-Economic and Religious Conditions, Art and Architecture, Literature",
                            "Harshavardhana and his Achievements",
                        ],
                    },
                    {
                        "id": "scr-hist-02",
                        "title": "Medieval India",
                        "points": [
                            "The Chola Administrative System",
                            "Delhi Sultanate and The Mughal Empire: Their Administration, Socio-Economic and Religious Conditions, Art and Architecture, Language and Literature",
                            "Bhakti and Sufi Movements",
                            "Shivaji and the Rise of Maratha Empire",
                            "Advent of Europeans",
                        ],
                    },
                    {
                        "id": "scr-hist-03",
                        "title": "Modern India",
                        "points": [
                            "1857 Revolt and its Impact",
                            "Rise and Consolidation of British Power in India",
                            "Changes in Administration, Social and Cultural Spheres",
                            "Social and Religious Reform Movements in the 19th and 20th Century",
                            "Indian National Movement: its various stages and important contributors and contributions from different parts of the country",
                            "Post Independence Consolidation and Reorganization within the country",
                        ],
                    },
                ],
            },
            {
                "title": "Geography",
                "marks": 30,
                "topics": [
                    {
                        "id": "scr-geo-01",
                        "title": "General & Physical Geography",
                        "points": [
                            "The Earth in our Solar System",
                            "Interior of the Earth",
                            "Major Landforms and their features",
                            "Climate: Structure and Composition of Atmosphere",
                            "Ocean Water: Tides, Waves, Currents",
                            "India and Andhra Pradesh: Major Physiographic features, Climate, Drainage System, Soils and Vegetation",
                            "Natural Hazards and Disasters and their Management",
                        ],
                    },
                    {
                        "id": "scr-geo-02",
                        "title": "Economic Geography of India & AP",
                        "points": [
                            "Natural Resources and their distribution",
                            "Agriculture and Agro-based Activities",
                            "Distribution of Major Industries and Major Industrial Regions",
                            "Transport, Communication, Tourism and Trade",
                        ],
                    },
                    {
                        "id": "scr-geo-03",
                        "title": "Human Geography of India & AP",
                        "points": [
                            "Human Development",
                            "Demographics",
                            "Urbanization and Migration",
                            "Racial, Tribal, Religious and Linguistic groups",
                        ],
                    },
                ],
            },
            {
                "title": "Indian Society",
                "marks": 30,
                "topics": [
                    {
                        "id": "scr-soc-01",
                        "title": "Structure of Indian Society",
                        "points": [
                            "Family, Marriage and Kinship",
                            "Caste, Tribe and Ethnicity",
                            "Religion and Women in Indian Society",
                        ],
                    },
                    {
                        "id": "scr-soc-02",
                        "title": "Social Issues",
                        "points": [
                            "Casteism, Communalism and Regionalisation",
                            "Crime against Women",
                            "Child Abuse and Child Labour",
                            "Youth Unrest and Agitation",
                        ],
                    },
                    {
                        "id": "scr-soc-03",
                        "title": "Welfare Mechanism",
                        "points": [
                            "Public Policies and Welfare Programmes",
                            "Constitutional and Statutory Provisions for Schedule Castes and Schedule Tribes",
                            "Provisions for Minorities, Backward Classes, Women, Disabled and Children",
                        ],
                    },
                ],
            },
            {
                "title": "Current Affairs",
                "marks": 30,
                "topics": [
                    {
                        "id": "scr-ca-01",
                        "title": "Current Affairs",
                        "points": [
                            "Major Current Events and Issues — International",
                            "Major Current Events and Issues — National",
                            "Major Current Events and Issues — State of Andhra Pradesh",
                        ],
                    },
                ],
            },
            {
                "title": "Mental Ability",
                "marks": 30,
                "topics": [
                    {
                        "id": "scr-ma-01",
                        "title": "Logical Reasoning",
                        "points": [
                            "Deductive, Inductive and Abductive Reasoning",
                            "Statement and Assumptions",
                            "Statement and Argument",
                            "Statement and Conclusion",
                            "Statement and Courses of Action",
                        ],
                    },
                    {
                        "id": "scr-ma-02",
                        "title": "Mental Ability",
                        "points": [
                            "Number Series and Letter Series",
                            "Odd Man Out",
                            "Coding and Decoding",
                            "Problems relating to Relations",
                            "Shapes and their Sub-Sections",
                        ],
                    },
                    {
                        "id": "scr-ma-03",
                        "title": "Basic Numeracy & Data Analysis",
                        "points": [
                            "Number System and Order of Magnitude",
                            "Averages, Ratio and Proportion, Percentage",
                            "Simple and Compound Interest",
                            "Time and Work; Time and Distance",
                            "Data Analysis: Tables, Bar Diagram, Line Graph, Pie-chart",
                        ],
                    },
                ],
            },
        ],
    },

    "paper1": {
        "label": "Paper 1",
        "subtitle": "AP Social & Cultural History + Indian Constitution | 150 Marks | 150 Min",
        "sections": [
            {
                "title": "Section A — Social & Cultural History of AP",
                "marks": 75,
                "topics": [
                    {
                        "id": "p1-aph-01",
                        "title": "1. Pre-historic Cultures & Early Dynasties",
                        "points": [
                            "Pre-Historic Cultures",
                            "The Satavahanas and The Ikshvakus: Socio-Economic and Religious Conditions, Literature, Art and Architecture",
                            "The Vishnukundins, The Eastern Chalukyas of Vengi, Andhra Cholas: Society, Religion, Telugu Language, Art and Architecture",
                        ],
                    },
                    {
                        "id": "p1-aph-02",
                        "title": "2. Dynasties of 11th–16th Century AD",
                        "points": [
                            "Various Major and Minor Dynasties that ruled Andhradesa between 11th and 16th centuries AD",
                            "Socio-Religious and Economic Conditions in Andhradesa (11th–16th century)",
                            "Growth of Telugu Language and Literature (11th–16th century)",
                            "Art and Architecture in Andhradesa (11th–16th century)",
                        ],
                    },
                    {
                        "id": "p1-aph-03",
                        "title": "3. Advent of Europeans to Independence (1885–1947)",
                        "points": [
                            "Advent of Europeans — Trade Centers",
                            "Andhra under the Company Rule",
                            "1857 Revolt and its Impact on Andhra",
                            "Establishment of British Rule",
                            "Socio-Cultural Awakening, Justice Party / Self Respect Movement",
                            "Growth of Nationalist Movement in Andhra between 1885 to 1947",
                            "Role of Socialists, Communists, Anti-Zamindari and Kisan Movements",
                            "Growth of Nationalist Poetry, Revolutionary Literature, Nataka Samasthalu and Women Participation",
                        ],
                    },
                    {
                        "id": "p1-aph-04",
                        "title": "4. Andhra Movement & Formation of Andhra State (1953)",
                        "points": [
                            "Origin and Growth of Andhra Movement",
                            "Role of Andhra Mahasabhas",
                            "Prominent Leaders of the Movement",
                            "Events leading to the formation of Andhra State 1953",
                            "Role of Press and Newspapers in the Andhra Movement",
                            "Role of Library Movement and Folk and Tribal Culture",
                        ],
                    },
                    {
                        "id": "p1-aph-05",
                        "title": "5. Formation of Andhra Pradesh (1956–2014)",
                        "points": [
                            "Events leading to the Formation of Andhra Pradesh State",
                            "Visalandhra Mahasabha",
                            "States Reorganization Commission and its Recommendations",
                            "Gentlemen Agreement",
                            "Important Social and Cultural Events between 1956 to 2014",
                        ],
                    },
                ],
            },
            {
                "title": "Section B — Indian Constitution",
                "marks": 75,
                "topics": [
                    {
                        "id": "p1-con-01",
                        "title": "6. Nature & Features of the Constitution",
                        "points": [
                            "Nature of Indian Constitution",
                            "Constitutional Development",
                            "Salient Features of Indian Constitution",
                            "Preamble",
                            "Fundamental Rights, Directive Principles of State Policy and their relationship",
                            "Fundamental Duties",
                            "Amendment of the Constitution",
                            "Basic Structure of the Constitution",
                        ],
                    },
                    {
                        "id": "p1-con-02",
                        "title": "7. Structure & Functions of Indian Government",
                        "points": [
                            "Structure and Functions: Legislative, Executive and Judiciary",
                            "Types of Legislatures: Unicameral and Bicameral",
                            "Executive — Parliamentary form",
                            "Judiciary — Judicial Review and Judicial Activism",
                        ],
                    },
                    {
                        "id": "p1-con-03",
                        "title": "8. Distribution of Powers — Union & States",
                        "points": [
                            "Distribution of Legislative and Executive Powers between the Union and the States",
                            "Legislative, Administrative and Financial Relations between the Union and the States",
                            "Powers and Functions of Constitutional Bodies",
                            "Human Rights Commission, RTI, Lokpal and Lok Ayukta",
                        ],
                    },
                    {
                        "id": "p1-con-04",
                        "title": "9. Centre–State Relations & Elections",
                        "points": [
                            "Centre-State Relations — Need for Reforms",
                            "Rajmannar Committee, Sarkaria Commission, M.M. Punchchi Commission",
                            "Unitary and Federal Features of Indian Constitution",
                            "Indian Political Parties — Party System in India",
                            "Recognition of National and State Parties",
                            "Elections and Electoral Reforms",
                            "Anti-Defection Law",
                        ],
                    },
                    {
                        "id": "p1-con-05",
                        "title": "10. Decentralisation & Panchayati Raj",
                        "points": [
                            "Centralisation vs Decentralisation",
                            "Community Development Programme",
                            "Balwant Rai Mehta Committee and Ashok Mehta Committee",
                            "73rd Constitutional Amendment Act and its Implementation",
                            "74th Constitutional Amendment Act and its Implementation",
                        ],
                    },
                ],
            },
        ],
    },

    "paper2": {
        "label": "Paper 2",
        "subtitle": "Indian & AP Economy + Science & Technology | 150 Marks | 150 Min",
        "sections": [
            {
                "title": "Section A — Indian & AP Economy",
                "marks": 75,
                "topics": [
                    {
                        "id": "p2-eco-01",
                        "title": "1. Economic Structure & Planning",
                        "points": [
                            "National Income of India: Concept and Measurement",
                            "Occupational Pattern and Sectoral Distribution of Income in India",
                            "Economic Growth and Economic Development",
                            "Strategy of Planning in India",
                            "New Economic Reforms 1991",
                            "Decentralization of Financial Resources",
                            "NITI Aayog",
                        ],
                    },
                    {
                        "id": "p2-eco-02",
                        "title": "2. Money, Banking, Public Finance & Foreign Trade",
                        "points": [
                            "Functions and Measures of Money Supply",
                            "Reserve Bank of India (RBI): Functions, Monetary Policy and Control of Credit",
                            "Indian Banking: Structure, Development and Reforms",
                            "Inflation: Causes and Remedies",
                            "India's Fiscal Policy: Fiscal Imbalance, Deficit Finance and Fiscal Responsibility",
                            "Indian Tax Structure — Goods and Services Tax (GST)",
                            "Recent Indian Budget",
                            "India's Balance of Payments (BOP) and FDI",
                        ],
                    },
                    {
                        "id": "p2-eco-03",
                        "title": "3. Agriculture, Industry & Services",
                        "points": [
                            "Indian Agriculture: Cropping Pattern, Agricultural Production and Productivity",
                            "Agricultural Finance and Marketing in India: Issues and Initiatives",
                            "Agricultural Pricing and Policy: MSP, Procurement, Issue Price and Distribution",
                            "Industrial Development in India: Patterns and Problems",
                            "New Industrial Policy 1991, Disinvestment, Ease of Doing Business",
                            "Industrial Sickness: Causes, Consequences and Remedial Measures",
                            "Services Sector: Growth and Contribution in India",
                            "Role of IT and ITES Industry in Development",
                        ],
                    },
                    {
                        "id": "p2-eco-04",
                        "title": "4. AP Economy & Public Finance",
                        "points": [
                            "Structure and Growth of AP Economy: GSDP and Sectoral Contribution",
                            "AP Per Capita Income (PCI)",
                            "AP State Revenue: Tax and Non-Tax Revenue",
                            "AP State Expenditure, Debts and Interest Payments",
                            "Central Assistance and Projects of External Assistance",
                            "Recent AP Budget",
                        ],
                    },
                    {
                        "id": "p2-eco-05",
                        "title": "5. AP Agriculture, Industry & Services",
                        "points": [
                            "Production Trends of Agriculture and Allied Sectors in AP",
                            "Cropping Pattern in AP",
                            "Rural Credit Cooperatives and Agricultural Marketing in AP",
                            "Strategies, Schemes and Programmes for Agricultural, Horticulture, Animal Husbandry, Fisheries and Forests",
                            "Growth and Structure of Industries in AP",
                            "Recent AP Industrial Development Policy, Single Window Mechanism, Industrial Incentives, MSMEs, Industrial Corridors",
                            "Structure and Growth of Services Sector in AP",
                            "Information Technology, Electronics and Communications in AP — Recent AP IT Policy",
                        ],
                    },
                ],
            },
            {
                "title": "Section B — Science & Technology",
                "marks": 75,
                "topics": [
                    {
                        "id": "p2-sci-01",
                        "title": "1. Technology Missions, Policies & Applications",
                        "points": [
                            "National S&T Policy: Recent Science, Technology and Innovation Policy, National Strategies and Missions, Emerging Technology Frontiers",
                            "Space Technology: Launch Vehicles of India, Recent Indian Satellite Launches and Applications, Indian Space Science Missions",
                            "Defence Technology: DRDO — Structure, Vision, Technologies Developed, Integrated Guided Missile Development Programme (IGMDP)",
                            "ICT: National Policy on Information Technology",
                            "Digital India Mission: Initiatives and Impact",
                            "E-Governance Programmes and Services — Cyber Security — National Cyber Security Policy",
                            "Nuclear Technology: Indian Nuclear Reactors and Nuclear Power Plants, Applications of Radioisotopes, India's Nuclear Programme",
                        ],
                    },
                    {
                        "id": "p2-sci-02",
                        "title": "2. Energy Management",
                        "points": [
                            "Installed Energy Capacities and Demand in India",
                            "National Energy Policy",
                            "National Policy on Biofuels",
                            "Bharat Stage Norms",
                            "Non-Renewable and Renewable Energy: Sources and Installed Capacities in India",
                            "New Initiatives and Recent Programmes, Schemes and Achievements in India's Renewable Energy Sector",
                        ],
                    },
                    {
                        "id": "p2-sci-03",
                        "title": "3. Ecosystem & Biodiversity",
                        "points": [
                            "Basic Concepts of Ecology — Ecosystem: Components and Types",
                            "Biodiversity: Meaning, Components and Biodiversity Hotspots",
                            "Loss of Biodiversity and Conservation: Methods, Recent Plans, Targets, Conventions and Protocols",
                            "Wildlife Conservation: CITES and Endangered Species with reference to India",
                            "Biosphere Reserves",
                            "Indian Wildlife Conservation efforts, projects, acts and initiatives in recent times",
                        ],
                    },
                    {
                        "id": "p2-sci-04",
                        "title": "4. Waste Management & Pollution Control",
                        "points": [
                            "Solid Wastes: Classification, Methods of Disposal and Management in India",
                            "Environmental Pollution: Types, Sources and Impacts",
                            "Pollution Control, Regulation and Alternatives: Recent projects, acts and initiatives to reduce Environmental Pollution in India",
                            "Impact of Transgenics on Environment and their Regulation",
                            "Eco-Friendly Technologies in Agriculture",
                            "Bioremediation: Types and Scope in India",
                        ],
                    },
                    {
                        "id": "p2-sci-05",
                        "title": "5. Environment & Health",
                        "points": [
                            "Global Warming, Climate Change, Acid Rain, Ozone Layer Depletion, Ocean Acidification",
                            "Recent International Initiatives, Protocols, Conventions to tackle Climate Change — India's Participation and Role",
                            "Sustainable Development: Meaning, Nature, Scope, Components and Goals",
                            "Health Issues: Recent Trends in Disease Burden and Epidemic/Pandemic Challenges in India",
                            "Preparedness and Response: Healthcare Delivery and Outcomes in India",
                            "Recent Public Health Initiatives and Programmes",
                        ],
                    },
                ],
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Group I — Official Syllabus Structure
# Source: APPSC Group I Syllabus PDF (4_PDFsam_APPSC_GROUP 1 SYLLABUS.pdf)
# ---------------------------------------------------------------------------
G1_STRUCTURE = {
    "prelims": {
        "label": "Prelims",
        "subtitle": "Screening Test | Paper I (120M) + Paper II (120M) | 240 Marks",
        "sections": [
            {
                "title": "Paper I — (A) History & Culture",
                "marks": 30,
                "topics": [
                    {
                        "id": "pre-ha-01",
                        "title": "1. Ancient India — Indus Valley to Guptas",
                        "points": [
                            "Indus Valley Civilization: Features, Sites, Society, Cultural History, Art and Religion",
                            "Vedic Age and Mahajanapadas",
                            "Religions: Jainism and Buddhism",
                            "The Magadhas, the Mauryan Empire — Administration, Socio-Economic and Religious Conditions, Art, Architecture, Literature, Science and Technology",
                            "Foreign Invasions on India and their Impact; the Kushans",
                            "The Satavahanas, the Sangam Age, the Sungas, the Gupta Empire",
                        ],
                    },
                    {
                        "id": "pre-ha-02",
                        "title": "2. South Indian Dynasties",
                        "points": [
                            "The Kanauj and their Contributions",
                            "The Badami Chalukyas, the Eastern Chalukyas, the Rashtrakutas",
                            "The Kalyani Chalukyas, the Cholas, the Hoysalas",
                            "The Yadavas, the Kakatiyas and the Reddis",
                        ],
                    },
                    {
                        "id": "pre-ha-03",
                        "title": "3. Medieval India — Sultanate, Vijayanagar & Mughals",
                        "points": [
                            "The Delhi Sultanate — Administration, Economy, Society, Religion, Literature, Arts and Architecture",
                            "The Vijayanagar Empire",
                            "The Mughal Empire — Administration, Economy, Society, Religion, Literature, Arts and Architecture",
                            "The Bhakti Movement and Sufism",
                        ],
                    },
                    {
                        "id": "pre-ha-04",
                        "title": "4. Europeans in India & British Expansion",
                        "points": [
                            "European Trading Companies in India — their struggle for supremacy",
                            "Special reference to Bengal, Bombay, Madras, Mysore, Andhra and Nizam",
                            "Governor-Generals and Viceroys",
                        ],
                    },
                    {
                        "id": "pre-ha-05",
                        "title": "5. 1857 & Reform Movements",
                        "points": [
                            "Indian War of Independence of 1857 — Origin, Nature, Causes, Consequences and Significance",
                            "Special reference to Concerned State",
                            "Religious and Social Reform Movements in 19th century in India and Concerned State",
                            "India's Freedom Movement",
                            "Revolutionaries in India and Abroad",
                        ],
                    },
                    {
                        "id": "pre-ha-06",
                        "title": "6. Gandhi, Independence & Post-Independence",
                        "points": [
                            "Mahatma Gandhi — his Thoughts, Principles and Philosophy",
                            "Important Satyagrahas",
                            "The Role of Sardar Patel and Subhash Chandra Bose in Freedom Movement",
                            "Post-independence Consolidation",
                            "Dr. B.R. Ambedkar — his Life and Contribution to making of Indian Constitution",
                            "India after Independence — Reorganization of the States in India",
                        ],
                    },
                ],
            },
            {
                "title": "Paper I — (B) Constitution, Polity, Social Justice & IR",
                "marks": 30,
                "topics": [
                    {
                        "id": "pre-cp-01",
                        "title": "1. Indian Constitution — Evolution & Features",
                        "points": [
                            "Indian Constitution: Evolution and Features",
                            "Preamble, Fundamental Rights, Fundamental Duties",
                            "Directive Principles of State Policy",
                            "Amendments, Significant Provisions and Basic Structure",
                        ],
                    },
                    {
                        "id": "pre-cp-02",
                        "title": "2. Union, States & Federal Structure",
                        "points": [
                            "Functions and Responsibilities of the Union and the States",
                            "Parliament and State Legislatures: Structure, Function, Power and Privileges",
                            "Issues and Challenges pertaining to Federal Structure",
                            "Devolution of Power and Finances up to local levels and Challenges therein",
                        ],
                    },
                    {
                        "id": "pre-cp-03",
                        "title": "3. Constitutional Authorities & Governance",
                        "points": [
                            "Constitutional Authorities: Powers, Functions and Responsibilities",
                            "Panchayati Raj",
                            "Public Policy and Governance",
                        ],
                    },
                    {
                        "id": "pre-cp-04",
                        "title": "4. LPG Impact & Regulatory Bodies",
                        "points": [
                            "Impact of Liberalization, Privatization and Globalization on Governance",
                            "Statutory, Regulatory and Quasi-judicial Bodies",
                        ],
                    },
                    {
                        "id": "pre-cp-05",
                        "title": "5. Rights Issues",
                        "points": [
                            "Human Rights",
                            "Women Rights",
                            "SC/ST Rights",
                            "Child Rights",
                        ],
                    },
                    {
                        "id": "pre-cp-06",
                        "title": "6. India's Foreign Policy & International Relations",
                        "points": [
                            "India's Foreign Policy",
                            "International Relations",
                            "Important International Institutions, Agencies and Fora — their Structure and Mandate",
                            "Important Policies and Programmes of Central and State Governments",
                        ],
                    },
                ],
            },
            {
                "title": "Paper I — (C) Indian & AP Economy & Planning",
                "marks": 30,
                "topics": [
                    {
                        "id": "pre-ec-01",
                        "title": "1. Indian Economy Basics & Planning",
                        "points": [
                            "Basic Characteristics of Indian Economy as a Developing Economy",
                            "Economic Development since Independence — Objectives and Achievements of Planning",
                            "NITI Aayog and its Approach to Economic Development",
                            "Growth and Distributive Justice — Human Development Index",
                            "Environmental Degradation and Challenges — Sustainable Development — Environmental Policy",
                        ],
                    },
                    {
                        "id": "pre-ec-02",
                        "title": "2. National Income, Poverty & Employment",
                        "points": [
                            "National Income — Concepts and Components — India's National Accounts",
                            "Demographic Issues",
                            "Poverty and Inequalities — Occupational Structure and Unemployment",
                            "Various Schemes of Employment and Poverty Eradication",
                            "Issues of Rural Development and Urban Development",
                        ],
                    },
                    {
                        "id": "pre-ec-03",
                        "title": "3. Agriculture, Industry & Economic Reforms",
                        "points": [
                            "Indian Agriculture — Irrigation, Inputs, Agricultural Strategy, Agrarian Crisis, Land Reforms",
                            "Agricultural Credit, Minimum Support Prices, Malnutrition and Food Security",
                            "Indian Industry — Industrial Policy, Make-in India, Start-up India, SEZs, Industrial Corridors",
                            "Energy and Power Policies",
                            "Economic Reforms — Liberalisation, Privatisation and Globalisation",
                            "International Trade, Balance of Payments and WTO",
                        ],
                    },
                    {
                        "id": "pre-ec-04",
                        "title": "4. Financial Institutions & Fiscal Policy",
                        "points": [
                            "Financial Institutions — RBI and Monetary Policy",
                            "Banking and Financial Sector Reforms, Commercial Banks and NPAs",
                            "Financial Markets — Stock Exchanges and SEBI",
                            "Indian Tax System and Recent Changes — GST and its Impact",
                            "Centre-States Financial Relations — Finance Commissions",
                            "Public Debt, Public Expenditure, Fiscal Policy and Budget",
                        ],
                    },
                    {
                        "id": "pre-ec-05",
                        "title": "5. Andhra Pradesh Economy",
                        "points": [
                            "Basic Features of AP Economy after Bifurcation in 2014",
                            "Impact of Bifurcation on Natural Resources, State Revenue, River Water Sharing",
                            "New Initiatives in Infrastructure, Power, Transport, IT and E-Governance",
                            "Approaches to Development in Agriculture, Industry and Social Sector",
                            "Urbanisation, Smart Cities, Skill Development and Employment",
                            "A.P. Reorganisation Act, 2014 — Economic Issues arising out of Bifurcation",
                            "Central Government's Assistance: New Capital, Backward Districts, Vizag Railway Zone, Kadapa Steel Factory, etc.",
                        ],
                    },
                ],
            },
            {
                "title": "Paper I — (D) Geography",
                "marks": 30,
                "topics": [
                    {
                        "id": "pre-ge-01",
                        "title": "1. General & Physical Geography",
                        "points": [
                            "Earth in Solar System, Motion of the Earth, Concept of Time and Seasons",
                            "Internal Structure of the Earth",
                            "Major Landforms and their Features",
                            "Atmosphere: Structure, Composition, Elements and Factors of Climate, Airmasses, Fronts, Atmospheric Disturbances, Climate Change",
                            "Oceans: Physical, Chemical and Biological Characteristics, Hydrological Disasters, Marine and Continental Resources",
                        ],
                    },
                    {
                        "id": "pre-ge-02",
                        "title": "2. Physical Features — India & AP",
                        "points": [
                            "World, India and AP: Major Physical Divisions",
                            "Earthquakes, Landslides",
                            "Natural Drainage, Climatic Changes and Regions, Monsoon",
                            "Natural Vegetation, Parks and Sanctuaries",
                            "Major Soil Types, Rocks and Minerals",
                        ],
                    },
                    {
                        "id": "pre-ge-03",
                        "title": "3. Social & Human Geography",
                        "points": [
                            "Distribution, Density, Growth and Sex-ratio of Population",
                            "Literacy and Occupational Structure",
                            "SC and ST Population",
                            "Rural-Urban Components",
                            "Racial, Tribal, Religious and Linguistic Groups",
                            "Urbanization, Migration and Metropolitan Regions",
                        ],
                    },
                    {
                        "id": "pre-ge-04",
                        "title": "4. Economic Geography",
                        "points": [
                            "World, India and AP: Major Sectors of Economy — Agriculture, Industry and Services",
                            "Basic Industries: Agro, Mineral, Forest, Fuel and Manpower Based",
                            "Transport and Trade: Pattern and Issues",
                        ],
                    },
                ],
            },
            {
                "title": "Paper II — (A) General Mental Ability",
                "marks": 60,
                "topics": [
                    {
                        "id": "pre-ma-01",
                        "title": "Reasoning & Analytical Ability",
                        "points": [
                            "Logical Reasoning and Analytical Ability",
                            "Number Series and Coding-Decoding",
                            "Problems Related to Relations",
                            "Shapes and their Sub-Sections, Venn Diagram",
                            "Problems based on Clocks, Calendar and Age",
                        ],
                    },
                    {
                        "id": "pre-ma-02",
                        "title": "Quantitative Aptitude",
                        "points": [
                            "Number System and Order of Magnitude",
                            "Ratio, Proportion and Variation",
                            "Central Tendencies — Mean, Median, Mode (including Weighted Mean)",
                            "Power and Exponent, Square, Square Root, Cube Root, HCF and LCM",
                            "Percentage, Simple and Compound Interest, Profit and Loss",
                            "Time and Work; Time and Distance; Speed and Distance",
                            "Area and Perimeter of Simple Geometrical Shapes; Volume and Surface Area of Sphere, Cone, Cylinder, Cubes and Cuboids",
                            "Lines, Angles and Common Geometrical Figures; Properties of Triangles, Quadrilateral, Rectangle, Parallelogram and Rhombus",
                            "Introduction to Algebra — BODMAS, Simplification",
                            "Data Interpretation, Data Analysis, Data Sufficiency and Probability",
                        ],
                    },
                    {
                        "id": "pre-ma-03",
                        "title": "Emotional & Social Intelligence",
                        "points": [
                            "Emotional Intelligence: Understanding and Analyzing Emotions, Dimensions of Emotional Intelligence, Coping with Emotions, Empathy and Coping with Stress",
                            "Social Intelligence, Interpersonal Skills, Decision Making, Critical Thinking, Problem Solving and Assessment of Personality",
                        ],
                    },
                ],
            },
            {
                "title": "Paper II — (B) Science, Technology & Current Events",
                "marks": 60,
                "topics": [
                    {
                        "id": "pre-st-01",
                        "title": "Science & Technology",
                        "points": [
                            "Nature and Scope of Science & Technology; Relevance to Day-to-Day Life",
                            "National Policy on Science, Technology and Innovation",
                            "Institutes and Organizations in India promoting S&T; Contribution of Prominent Indian Scientists",
                            "ICT: Nature, Scope, ICT in Day-to-Day Life, Industry and Governance; E-Governance; Cyber Security — National Cyber Crime Policy",
                            "Space & Defence: ISRO — Activities and Achievements; Various Satellite Programmes; DRDO — Vision, Mission and Activities",
                            "Energy: India's Energy Needs and Deficit; Energy Resources; Government Policies — Solar, Wind and Nuclear Energy",
                            "Environmental Science: Environment Issues; Biodiversity; Climate Change; Forest and Wildlife Conservation; Environmental Hazards; Biotechnology and Nanotechnology; Genetic Engineering; Health & Environment",
                        ],
                    },
                    {
                        "id": "pre-st-02",
                        "title": "Current Events",
                        "points": [
                            "Current Events of Regional Importance",
                            "Current Events of National Importance",
                            "Current Events of International Importance",
                        ],
                    },
                ],
            },
        ],
    },

    "telugu": {
        "label": "Mains: Telugu",
        "subtitle": "Qualifying Nature | 150 Marks | 180 Min",
        "sections": [
            {
                "title": "Telugu Syllabus (SSC Standard)",
                "marks": 150,
                "topics": [
                    {
                        "id": "tel-01",
                        "title": "Topics",
                        "points": [
                            "Essay (Minimum 200 words, Maximum 250 words)",
                            "To elaborate the thought of poetic or verse",
                            "Precis Writing (1/3rd summary)",
                            "Comprehension (Reading passage followed by questions)",
                            "Formal Speech (Welcome, Farewell, Inauguration, etc.)",
                            "Prepare Statements for publicity media",
                            "Letter Writing",
                            "Debate Writing",
                            "Application Writing",
                            "Report Writing",
                            "Dialogue Writing or Dialogue Skills",
                            "Translation (English to Telugu)",
                            "Grammar of Telugu"
                        ]
                    }
                ]
            }
        ]
    },

    "english": {
        "label": "Mains: English",
        "subtitle": "Qualifying Nature | 150 Marks | 180 Min",
        "sections": [
            {
                "title": "English Syllabus (SSC Standard)",
                "marks": 150,
                "topics": [
                    {
                        "id": "eng-01",
                        "title": "Topics",
                        "points": [
                            "Essay (Descriptive, analytical, philosophical, based on Current Affairs)",
                            "Letter Writing (Formal letter)",
                            "Press Release / Appeal",
                            "Report Writing",
                            "Writing on Visual Information",
                            "Formal Speech",
                            "Precis Writing",
                            "Reading Comprehension",
                            "English Grammar",
                            "Translation (Regional Language to English)"
                        ]
                    }
                ]
            }
        ]
    },

    "paper1": {
        "label": "Mains: Paper I",
        "subtitle": "General Essay | 150 Marks | 180 Min",
        "sections": [
            {
                "title": "General Essay",
                "marks": 150,
                "topics": [
                    {
                        "id": "m1-ge-01",
                        "title": "Section I, II & III",
                        "points": [
                            "Current Affairs",
                            "Socio-political issues",
                            "Socio-economic issues",
                            "Socio-environmental issues",
                            "Cultural and historical aspects",
                            "Issues related to civic awareness",
                            "Reflective topics"
                        ]
                    }
                ]
            }
        ]
    },

    "paper2": {
        "label": "Mains: Paper II",
        "subtitle": "History, Culture & Geography of India and AP | 150 Marks | 180 Min",
        "sections": [
            {
                "title": "Section A — History & Culture of India",
                "marks": 60,
                "topics": [
                    {
                        "id": "m2-hi-01",
                        "title": "1. Pre-Historic to Kushans",
                        "points": [
                            "Pre-Historic Cultures in India",
                            "Indus Valley Civilization, Vedic Culture, Mahajanapadas",
                            "Emergence of New Religions — Jainism and Buddhism",
                            "Rise of the Magadha and Age of the Mauryas — Ashoka Dharma",
                            "Foreign Invasions on India; the Kushans",
                            "The Satavahanas, the Sangam Age, the Sungas, the Guptas, the Kanauj",
                            "Historical Accounts of Foreign Travelers; Early Educational Institutions",
                        ],
                    },
                    {
                        "id": "m2-hi-02",
                        "title": "2. South Indian Dynasties to Delhi Sultanate",
                        "points": [
                            "The Pallavas, the Badami Chalukyas, the Eastern Chalukyas, the Rashtrakutas, the Kalyani Chalukyas and the Cholas",
                            "Socio-Cultural Contributions, Language, Literature, Art and Architecture",
                            "Delhi Sultanates — Advent of Islam and its Impact",
                            "Religious Movements — Bhakti and Sufi and their Influence",
                            "Growth of Vernacular Languages, Scripts, Literature and Fine Arts",
                            "Socio-Cultural Conditions of the Kakatiyas, Vijayanagaras, Bahmanis, Qutubshahis and their Contemporary South Indian Kingdoms",
                        ],
                    },
                    {
                        "id": "m2-hi-03",
                        "title": "3. Mughals, Marathas & Europeans",
                        "points": [
                            "The Mughals — Administration, Socio-Religious Life and Cultural Developments",
                            "Shivaji and Rise of Maratha Empire",
                            "Advent of Europeans in India — Trade Practices",
                            "Rise of East India Company — its Hegemony",
                            "Changes in Administration, Social and Cultural Spheres",
                            "Role of Christian Missionaries",
                        ],
                    },
                    {
                        "id": "m2-hi-04",
                        "title": "4. British Rule, 1857 & Social Reform Movements",
                        "points": [
                            "Rise of British Rule in India from 1757 to 1856",
                            "Land Revenue Settlements — Permanent Settlement, Ryotwari and Mahalwari",
                            "1857 Revolt and its Impact",
                            "Education, Press and Cultural Changes",
                            "Rise of National Consciousness and Changes",
                            "Socio-Religious Reform Movements in 19th Century — Rajaram Mohan Roy, Dayananda Saraswathi, Swami Vivekananda, Annie Besant, Sir Syed Ahmad Khan and others",
                        ],
                    },
                    {
                        "id": "m2-hi-05",
                        "title": "5. Indian Nationalism & Independence",
                        "points": [
                            "Rise of Indian Nationalism — Activities of Indian National Congress",
                            "Vandemataram, Home Rule Movements, Self Respect Movement",
                            "Jyothiba Phule, Narayana Guru, Periyar Ramaswamy Naicker",
                            "Role of Mahatma Gandhi, Subhash Chandra Bose, Vallabhai Patel — Satyagraha, Quit India Movement",
                            "Dr. B.R. Ambedkar and his Contributions",
                            "Indian Nationalism in Three Phases — Freedom Struggle 1885-1905, 1905-1920 and Gandhi Phase 1920-1947",
                            "Peasant, Women, Tribal and Workers Movements; Role of Different Parties in Freedom Struggle",
                            "Independence and Partition of India; India after Independence",
                            "Rehabilitation after Partition; Linguistic Re-organization of States; Integration of Indian States",
                        ],
                    },
                ],
            },
            {
                "title": "Section B — History & Culture of Andhra Pradesh",
                "marks": 60,
                "topics": [
                    {
                        "id": "m2-ap-01",
                        "title": "6. Ancient Andhra",
                        "points": [
                            "The Satavahanas, the Ikshvakus, the Salankayanas, the Pallavas and the Vishnukundins",
                            "Social and Economic Conditions — Religion, Language (Telugu), Literature, Art and Architecture",
                            "Jainism and Buddhism in Andhra",
                            "The Eastern Chalukyas, the Rashtrakutas, the Renati Cholas and others",
                            "Socio-Cultural Life, Religion, Telugu Script and Language, Literature, Art and Architecture",
                        ],
                    },
                    {
                        "id": "m2-ap-02",
                        "title": "7. Medieval Andhra (1000–1565 AD)",
                        "points": [
                            "Socio-Cultural and Religious Conditions in Andhradesa 1000 to 1565 AD",
                            "Antiquity, Origin and Growth of Telugu Language and Literature (Kavitraya, Ashtadiggajas)",
                            "Fine Arts, Art & Architecture during the reign of Kakatiyas, Reddis, Gajapatis and Vijayanagaras and their Feudatories",
                            "Historical Monuments — Significance",
                            "Contribution of Qutubshahis to Andhra History and Culture",
                            "Regional Literature — Praja Kavi Vemana and others",
                        ],
                    },
                    {
                        "id": "m2-ap-03",
                        "title": "8. Modern Andhra — Social Awakening",
                        "points": [
                            "European Trade Establishments in Andhra",
                            "Andhra under the Company Rule",
                            "Role of Christian Missionaries",
                            "Socio-Cultural and Literary Awakening — C.P. Brown, Thamos Munro, Mackenzie",
                            "Zamindary and Polegary System; Native States and Little Kings",
                            "Role of Social Reformers — Gurajada Apparao, Kandukuri Veeresalingam, Raghupati Venkataratnam Naidu, Gidugu Ramamurthy, Annie Besant and others",
                            "Library Movement in AP; Role of Newspapers; Folk and Tribal Culture, Oral Traditions, Subaltern",
                        ],
                    },
                    {
                        "id": "m2-ap-04",
                        "title": "9. Andhra Movement & State Formation",
                        "points": [
                            "Role of Social Reformers in Nationalist Movement in Andhra",
                            "Andhra Mahasabha and the Andhra Movement",
                            "Formation of Andhra State (1953)",
                            "Visalandhra Movement",
                            "Formation of Andhra Pradesh (1956)",
                        ],
                    },
                    {
                        "id": "m2-ap-05",
                        "title": "10. AP 1956–2014 & Bifurcation",
                        "points": [
                            "Important Social and Cultural Events between 1956 to 2014",
                            "AP Reorganisation Act, 2014",
                            "Effect of Bifurcation on Trade, Commerce and Industry",
                            "Implication of Financial Resources of State Government",
                            "Developmental Opportunities — Socio-Economic, Cultural and Demographic Impact of Bifurcation",
                            "Impact on River Water Sharing and other Link Issues",
                        ],
                    },
                ],
            },
            {
                "title": "Section C — Geography: India & AP",
                "marks": 30,
                "topics": [
                    {
                        "id": "m2-ge-01",
                        "title": "11. Physical Features & Resources",
                        "points": [
                            "India and AP: Major Landforms, Climatic Changes, Soil Types",
                            "Rivers, Water Streams, Geology, Rocks and Mineral Resources",
                            "Metals, Clays and Construction Materials",
                            "Reservoirs and Dams",
                            "Forests — Mountains, Hills, Flora and Fauna, Plateau Forests, Hill Forests, Vegetation Classification",
                        ],
                    },
                    {
                        "id": "m2-ge-02",
                        "title": "12. Economic Geography",
                        "points": [
                            "Agriculture, Livestock, Forestry and Fishery",
                            "Quarrying and Mining",
                            "Household Manufacturing and Industries — Agro, Mineral, Forest, Fuel and Manpower Based",
                            "Trade and Commerce, Communication, Road Transport, Storage",
                        ],
                    },
                    {
                        "id": "m2-ge-03",
                        "title": "13–14. Social & Faunal-Floral Geography",
                        "points": [
                            "Population Movements and Distribution — Density, Age, Sex, Rural-Urban",
                            "Race, Caste, Tribe, Religion, Linguistic Groups, Urban Migration, Education Characteristics",
                            "Wild Animals, Birds, Reptiles, Mammals, Trees and Plants",
                        ],
                    },
                    {
                        "id": "m2-ge-04",
                        "title": "15. Environmental Geography",
                        "points": [
                            "Sustainable Development, Globalisation",
                            "Temperature, Humidity, Cloudiness, Winds and Special Weather Phenomena",
                            "Natural Hazards — Earthquakes, Landslides, Floods, Cyclones, Cloud Burst",
                            "Disaster Management and Impact Assessment",
                            "Environmental Pollution and Pollution Management",
                        ],
                    },
                ],
            },
        ],
    },

    "paper3": {
        "label": "Mains: Paper III",
        "subtitle": "Polity, Constitution, Governance, Law & Ethics | 150 Marks | 180 Min",
        "sections": [
            {
                "title": "(A) Indian Polity & Constitution",
                "marks": 50,
                "topics": [
                    {
                        "id": "m3-pc-01",
                        "title": "1. Indian Constitution — Salient Features",
                        "points": [
                            "Indian Constitution and its Salient Features",
                            "Functions and Duties of the Indian Union and the State Governments",
                        ],
                    },
                    {
                        "id": "m3-pc-02",
                        "title": "2. Federal Structure & Distribution of Powers",
                        "points": [
                            "Issues and Challenges pertaining to the Federal Structure",
                            "Role of Governor in States",
                            "Distribution of Powers between the Union and States (Union List, State List and Concurrent List)",
                        ],
                    },
                    {
                        "id": "m3-pc-03",
                        "title": "3. Local Governance & Constitutional Authorities",
                        "points": [
                            "Rural and Urban Local Governance under 73rd and 74th Constitutional Amendment",
                            "Constitutional Authorities and their Role",
                        ],
                    },
                    {
                        "id": "m3-pc-04",
                        "title": "4. Parliament & State Legislatures",
                        "points": [
                            "Parliament and State Legislatures — Structure, Functioning, Conduct of Business",
                            "Powers & Privileges and Issues arising out of these",
                        ],
                    },
                    {
                        "id": "m3-pc-05",
                        "title": "5. Judiciary",
                        "points": [
                            "Judiciary in India — Structure and Functions",
                            "Important Provisions relating to Emergency and Constitutional Amendments",
                            "Judicial Review and Public Interest Litigation (PIL)",
                        ],
                    },
                ],
            },
            {
                "title": "(B) Public Administration & Governance",
                "marks": 50,
                "topics": [
                    {
                        "id": "m3-pa-01",
                        "title": "6. Nature & Scope of Public Administration",
                        "points": [
                            "Meaning, Nature and Scope of Public Administration",
                            "Evolution in India",
                            "Administrative Ideas in Kautilya's Arthashastra",
                            "Mughal Administration",
                            "Legacy of British Rule",
                        ],
                    },
                    {
                        "id": "m3-pa-02",
                        "title": "7–8. Government Policies, Civil Society & NGOs",
                        "points": [
                            "Government Policies and Interventions for Development in various Sectors",
                            "Issues and Problems of Implementation",
                            "Development Processes — Role of Civil Society, NGOs and other Stakeholders",
                        ],
                    },
                    {
                        "id": "m3-pa-03",
                        "title": "9. Statutory, Regulatory Bodies & Civil Services",
                        "points": [
                            "Statutory, Regulatory and various Quasi-judicial Authorities",
                            "Role of Civil Services in Democracy",
                        ],
                    },
                    {
                        "id": "m3-pa-04",
                        "title": "10. Good Governance & E-Governance",
                        "points": [
                            "Good Governance and E-Governance",
                            "Transparency, Accountability and Responsiveness in Governance",
                            "Citizen's Charter",
                            "RTI, Public Service Act and their Implications",
                            "Concept of Social Audit and its Importance",
                        ],
                    },
                ],
            },
            {
                "title": "(C) Ethics in Public Service & Law",
                "marks": 50,
                "topics": [
                    {
                        "id": "m3-et-01",
                        "title": "11. Ethics & Human Interface",
                        "points": [
                            "Essence, Determinants and Consequences of Ethics in Human Actions",
                            "Dimensions of Ethics",
                            "Ethics in Private and Public Relationships",
                            "Ethics, Integrity and Accountability in Public Service",
                        ],
                    },
                    {
                        "id": "m3-et-02",
                        "title": "12–13. Human Values, Attitude & Emotional Intelligence",
                        "points": [
                            "Human Values — Harmony in Existence, Human Relationships in Society and Nature",
                            "Gender Equality; Role of Family, Society and Educational Institutions in Imparting Values",
                            "Lessons from Lives and Teachings of Great Leaders and Reformers",
                            "Attitude: Content, Functions, Influence and Relation with Thought and Behaviour",
                            "Moral and Political Attitudes; Role of Social Influence and Persuasion",
                            "Emotional Intelligence — Concepts, Utilities and Application in Administration and Governance",
                        ],
                    },
                    {
                        "id": "m3-et-03",
                        "title": "14. Public Service Ethics & Codes of Conduct",
                        "points": [
                            "Concept of Public Service — Philosophical Basis of Governance",
                            "Professional Ethics — Codes of Ethics, Codes of Conduct",
                            "RTI, Public Service Act, Leadership Ethics, Work Culture",
                            "Ethical and Moral Values in Governance",
                            "Ethical Issues in International Relations, Corruption, Lokpal and Lokayukta",
                        ],
                    },
                    {
                        "id": "m3-et-04",
                        "title": "15. Basic Knowledge of Laws in India",
                        "points": [
                            "Constitution of India — Nature, Salient Features, Fundamental Rights, DPSP, Bifurcation of Powers, Powers of Judiciary/Executive/Legislature",
                            "Civil and Criminal Laws — Hierarchy of Courts, Difference between Substantial and Procedural Laws, Order and Decree, New Developments in Criminal Laws (Nirbhaya Act)",
                            "Labour Law — Concept of Social Welfare Legislations, Changing Trends in Employment, New Labour Laws",
                            "Cyber Laws — Information Technology Act, Cyber Security and Cyber Crime, Jurisdiction Issues",
                            "Tax Laws — Income, Profits, Wealth Tax, Corporate Tax and GST",
                        ],
                    },
                ],
            },
        ],
    },

    "paper4": {
        "label": "Mains: Paper IV",
        "subtitle": "Economy & Development of India and AP | 150 Marks | 180 Min",
        "sections": [
            {
                "title": "Indian Economy — Macro & Challenges",
                "marks": 60,
                "topics": [
                    {
                        "id": "m4-ec-01",
                        "title": "1. Major Challenges of Indian Economy",
                        "points": [
                            "Inconsistent Growth Rate, Low Growth Rates of Agriculture and Manufacturing",
                            "Inflation and Oil Prices, Current Account Deficit and Unfavourable Balance of Payments",
                            "Falling Rupee Value, Growing NPAs and Capital Infusion",
                            "Money Laundering and Black Money",
                            "Insufficient Financial Resources and Deficiency of Capital",
                            "Lack of Inclusive Growth and Sustainable Development",
                        ],
                    },
                    {
                        "id": "m4-ec-02",
                        "title": "2. Resource Mobilization in Indian Economy",
                        "points": [
                            "Sources of Financial Resources for Public and Private Sectors",
                            "Budgetary Resources — Tax Revenue and Non-Tax Revenue",
                            "Public Debt — Market Borrowings, Loans and Grants, External Debt from Multilateral Agencies",
                            "Foreign Institutional Investment (FII) and Foreign Direct Investment (FDI)",
                            "Monetary and Fiscal Policies",
                            "Financial Markets and Institutions of Developmental Finance",
                            "Physical Resources — Energy Resources",
                        ],
                    },
                    {
                        "id": "m4-ec-03",
                        "title": "4. Government Budgeting",
                        "points": [
                            "Structure of Government Budget and its Components",
                            "Budgeting Process and Recent Changes — Types of Budget",
                            "Types of Deficits, their Impact and Management",
                            "Highlights and Analysis of Current Year's Union Budget",
                            "GST and Related Issues",
                            "Central Assistance to States",
                            "Issues of Federal Finance in India",
                            "Recommendations of the Latest Finance Commission",
                        ],
                    },
                    {
                        "id": "m4-ec-04",
                        "title": "6. Inclusive Growth",
                        "points": [
                            "Meaning of Inclusion — Causes of Exclusion in India",
                            "Strategies for Inclusion — Poverty Alleviation and Employment",
                            "Health, Education, Women Empowerment, Social Welfare Schemes",
                            "Food Security and Public Distribution System",
                            "Sustainable Agriculture — Integrated Rural Development — Regional Diversification",
                            "Public and Partnership for Inclusive Growth — Financial Inclusion",
                            "All AP Government's Current Schemes for Inclusive Growth and Financial Inclusion",
                        ],
                    },
                    {
                        "id": "m4-ec-05",
                        "title": "7. Agricultural Development",
                        "points": [
                            "Role of Agriculture in Economic Development — Contribution to GDP",
                            "Issues of Finance, Production and Marketing",
                            "Green Revolution and Changing Focus to Dryland Farming, Organic Farming and Sustainable Agriculture",
                            "Minimum Support Prices — Agriculture Policy",
                            "Swaminathan Commission — Rainbow Revolution",
                        ],
                    },
                    {
                        "id": "m4-ec-06",
                        "title": "9. Industrial Development & Policy",
                        "points": [
                            "Role of Industrial Sector in Economic Development",
                            "Evolution of Industrial Policy since Independence",
                            "Industrial Policy 1991 and its Impact on Indian Economy",
                            "Contribution of Public Sector to Industrial Development in India",
                            "Impact of LPG on Industrial Development — Disinvestment and Privatization",
                            "Micro, Small and Medium Enterprises (MSMEs) — Problems and Policy",
                            "Industrial Sickness and Support Mechanism",
                            "Manufacturing Policy — Make-in India — Start-up Programme — NIMZs — SEZs — Industrial Corridors",
                        ],
                    },
                    {
                        "id": "m4-ec-07",
                        "title": "11. Infrastructure in India",
                        "points": [
                            "Transport Infrastructure — Ports, Roads, Airports, Railways",
                            "Communication Infrastructure — IT, E-Governance, Digital India",
                            "Energy and Power; Urban Infrastructure — Smart Cities, Solid Waste Management",
                            "Weather Forecast and Disaster Management",
                            "Issues of Finance, Ownership, Operation and Maintenance of Infrastructure",
                            "Public-Private Partnership and Related Issues",
                            "Pricing of Public Utilities and Government Policy",
                            "Environmental Impacts of Infrastructure Projects",
                        ],
                    },
                ],
            },
            {
                "title": "Andhra Pradesh Economy",
                "marks": 45,
                "topics": [
                    {
                        "id": "m4-ap-01",
                        "title": "3. Resource Mobilization in AP",
                        "points": [
                            "Budgetary Resources and Constraints in AP",
                            "Fulfillment of Conditions of AP Bifurcation Act",
                            "Central Assistance and Issues of Conflict",
                            "Public Debt and Projects of External Assistance",
                            "Physical Resources — Mineral and Forest Resources",
                            "Water Disputes with Neighbouring States",
                        ],
                    },
                    {
                        "id": "m4-ap-02",
                        "title": "5. Government Budgeting in AP",
                        "points": [
                            "Budget Constraints in AP",
                            "Central Assistance and Issues of Conflict after Bifurcation",
                            "Management of Deficits",
                            "Highlights and Analysis of the Current Year AP Budget",
                            "State Finance Commission and Local Finance in AP",
                        ],
                    },
                    {
                        "id": "m4-ap-03",
                        "title": "8. Agricultural Development in AP",
                        "points": [
                            "Contribution of Agriculture to SGDP in AP",
                            "Regional Disparities in Irrigation and Agricultural Development",
                            "Changing Cropping Pattern — Focus on Horticulture, Fisheries and Dairying",
                            "Government Schemes to Promote Agriculture in AP",
                        ],
                    },
                    {
                        "id": "m4-ap-04",
                        "title": "10. Industrial Policy of AP",
                        "points": [
                            "AP Government's Industrial Policy — Incentives to Industries",
                            "Industrial Corridors and SEZs in Andhra Pradesh",
                            "Bottlenecks for Industrial Development",
                            "Power Projects",
                        ],
                    },
                    {
                        "id": "m4-ap-05",
                        "title": "12. Infrastructure Development in AP",
                        "points": [
                            "Transport Infrastructure in AP",
                            "Energy and ICT Infrastructure in AP",
                            "Bottlenecks and Government Policy",
                            "Ongoing Projects",
                        ],
                    },
                ],
            },
        ],
    },

    "paper5": {
        "label": "Mains: Paper V",
        "subtitle": "Science, Technology & Environmental Issues | 150 Marks | 180 Min",
        "sections": [
            {
                "title": "Science, Technology & Innovation",
                "marks": 50,
                "topics": [
                    {
                        "id": "m5-st-01",
                        "title": "1. Integration of S&T for Human Life",
                        "points": [
                            "Integration of Science, Technology and Innovation for Better Human Life",
                            "Science & Technology in Everyday Life",
                            "National Policies on Proliferation of Science, Technology and Innovation",
                            "India's Contribution in the Field of Science and Technology",
                            "Concerns and Challenges in Proliferation and Use of S&T",
                            "Role and Scope of S&T in Nation Building",
                            "Major Scientific Institutes for Research and Development in AP and India",
                            "Achievements of Indian Scientists; Indigenous Technologies",
                        ],
                    },
                    {
                        "id": "m5-st-02",
                        "title": "2. ICT, E-Governance & Cyber Security",
                        "points": [
                            "Information and Communication Technology (ICT) — Importance, Advantages and Challenges",
                            "E-Governance and India",
                            "Cyber Crime and Policies to Address Security Concerns",
                            "Government of India Policy on Information Technology",
                            "IT Development in AP and India",
                        ],
                    },
                    {
                        "id": "m5-st-03",
                        "title": "3. Indian Space Programme & DRDO",
                        "points": [
                            "Indian Space Programme — Past, Present and Future",
                            "ISRO — Activities and Achievements",
                            "Satellite Programmes of India — Use of Satellites in Health, Education, Communication, Weather Forecasting",
                            "Defence Research and Development Organisation (DRDO)",
                        ],
                    },
                    {
                        "id": "m5-st-04",
                        "title": "4. Energy & Nuclear Policy",
                        "points": [
                            "India's Energy Needs, Efficiency and Resources",
                            "Clean Energy Resources",
                            "Energy Policy of India — Government Policies and Programmes",
                            "Conventional Energy: Thermal Power",
                            "Non-Conventional/Renewable Energy: Solar, Wind, Bio, Waste-Based, Geothermal, Tidal",
                            "Salient Features of Nuclear Policy of India",
                            "Development of Nuclear Programmes in India",
                            "Nuclear Policies at the International Level and India's Stand",
                        ],
                    },
                    {
                        "id": "m5-st-05",
                        "title": "7. Biotechnology & Nanotechnology",
                        "points": [
                            "Nature, Scope and Applications of Biotechnology and Nanotechnology in India",
                            "Ethical, Social and Legal Concerns — Government Policies",
                            "Genetic Engineering — Issues and Impact on Human Life",
                            "Biodiversity, Fermentation, Immuno-Diagnosis Techniques",
                        ],
                    },
                    {
                        "id": "m5-st-06",
                        "title": "8. Human Diseases & Biotechnology in Agriculture",
                        "points": [
                            "Human Diseases — Microbial Infections",
                            "Common Infections and Preventive Measures — Bacterial, Viral, Protozoal and Fungal",
                            "Diarrhoea, Dysentery, Cholera, Tuberculosis, Malaria, HIV, Encephalitis, Chikungunya, Bird Flu",
                            "Introduction to Genetic Engineering and Biotechnology",
                            "Tissue Culture Methods and Applications",
                            "Biotechnology in Agriculture — Bio-Pesticides, Bio-Fertilizers, Bio-Fuels, GM Crops",
                            "Animal Husbandry — Transgenic Animals",
                            "Vaccines — Introduction to Immunity, Fundamental Concepts in Vaccination",
                        ],
                    },
                    {
                        "id": "m5-st-07",
                        "title": "9. Intellectual Property Rights in S&T",
                        "points": [
                            "Issues related to Intellectual Property Rights in the Field of Science and Technology",
                            "Promotion of Science in AP and India",
                        ],
                    },
                ],
            },
            {
                "title": "Environment & Ecology",
                "marks": 50,
                "topics": [
                    {
                        "id": "m5-ev-01",
                        "title": "5. Development vs Environment",
                        "points": [
                            "Development vs Nature / Environment",
                            "Depletion of Natural Resources — Metals, Minerals — Conservation Policy",
                            "Environmental Pollution — Natural and Anthropogenic; Environmental Degradation",
                            "Sustainable Development — Possibilities and Challenges",
                            "Climate Change and its Effect on the World — Climate Justice",
                            "Environment Impact Assessment",
                            "Natural Disasters — Cyclones, Earthquakes, Landslides, Tsunamis — Prediction Management",
                            "Correlation between Health & Environment",
                            "Social Forestry, Afforestation and Deforestation; Mining in AP and India",
                        ],
                    },
                    {
                        "id": "m5-ev-02",
                        "title": "6. Pollution, Solid Waste & Global Environmental Issues",
                        "points": [
                            "Environmental Pollution: Sources, Impacts and Control of Air, Water and Soil Pollution",
                            "Noise Pollution",
                            "Solid Waste Management — Types, Impacts, Recycling and Reuse",
                            "Remedial Measures for Soil Erosion and Coastal Erosion",
                            "Global Environmental Issues: Role of IT in Environment and Human Health",
                            "Ozone Layer Depletion, Acid Rain, Global Warming and its Impacts",
                            "Environmental Legislation: Montreal Protocol, Kyoto Protocol, UNFCCC, CITES",
                            "Environment (Protection) Act 1986, Forest Conservation Act, Wildlife Protection Act",
                            "Biodiversity Bill, COP 21, Sustainable Development Goals (SDGs)",
                            "National Disaster Management Policy 2016",
                            "White Revolution, Green Revolution and Green Pharmacy",
                        ],
                    },
                ],
            },
            {
                "title": "Natural Resources",
                "marks": 50,
                "topics": [
                    {
                        "id": "m5-nr-01",
                        "title": "Natural Resources — Types & Conservation",
                        "points": [
                            "Types of Natural Resources — Renewable and Non-Renewable",
                            "Forest Resources",
                            "Fishery Resources",
                            "Fossil Fuels — Coal, Petroleum and Natural Gas",
                            "Mineral Resources",
                            "Water Resources — Types, Watershed Management",
                            "Land Resources — Types of Soils and Soil Reclamation",
                        ],
                    },
                ],
            },
        ],
    },
}


async def homepage(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "current_user": get_current_user(request),
    })


async def group1(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "group1.html", {
        "structure": G1_STRUCTURE,
        "structure_json": json.dumps(G1_STRUCTURE),
        "shared_topics_json": json.dumps(SHARED_TOPICS),
        "current_user": user,
        "user_id": user["id"] if user else None,
    })


async def group2(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "group2.html", {
        "structure": G2_STRUCTURE,
        "structure_json": json.dumps(G2_STRUCTURE),
        "shared_topics_json": json.dumps(SHARED_TOPICS),
        "current_user": user,
        "user_id": user["id"] if user else None,
    })






# ---------------------------------------------------------------------------
# Cross-Syllabus Shared Topics — Complete bidirectional map
# Covers: G1 Prelims ↔ G2 Screening, G1 Prelims ↔ G1 Mains,
#         G1 Mains ↔ G2 Mains, G2 Screening ↔ G2 Mains
# ---------------------------------------------------------------------------

SHARED_TOPICS = {

    # ── HISTORY ─────────────────────────────────────────────────────────────

    # G1 Prelims History ↔ G2 Screening History
    "pre-ha-01": [{"id": "cg-harappan-civilization", "label": "Focused: Indus Valley Civilization"},
                  {"id": "scr-hist-01", "label": "G2 Screening: Ancient India"},
                  {"id": "m2-hi-01",    "label": "G1 Mains P2: Pre-Historic to Kushans"}],
    "pre-ha-02": [{"id": "scr-hist-01", "label": "G2 Screening: Ancient India"},
                  {"id": "m2-hi-02",    "label": "G1 Mains P2: South Indian Dynasties"}],
    "pre-ha-03": [{"id": "scr-hist-02", "label": "G2 Screening: Medieval India"},
                  {"id": "m2-hi-02",    "label": "G1 Mains P2: South Indian Dynasties to Delhi Sultanate"},
                  {"id": "m2-hi-03",    "label": "G1 Mains P2: Mughals, Marathas & Europeans"}],
    "pre-ha-04": [{"id": "scr-hist-02", "label": "G2 Screening: Medieval India"},
                  {"id": "scr-hist-03", "label": "G2 Screening: Modern India"},
                  {"id": "m2-hi-03",    "label": "G1 Mains P2: Mughals, Marathas & Europeans"}],
    "pre-ha-05": [{"id": "scr-hist-03", "label": "G2 Screening: Modern India"},
                  {"id": "m2-hi-04",    "label": "G1 Mains P2: British Rule, 1857 & Reform Movements"}],
    "pre-ha-06": [{"id": "scr-hist-03", "label": "G2 Screening: Modern India"},
                  {"id": "m2-hi-05",    "label": "G1 Mains P2: Indian Nationalism & Independence"}],

    # G2 Screening History ↔ G1 Prelims + G1 Mains + G2 Paper 1 AP History
    "scr-hist-01": [{"id": "pre-ha-01", "label": "G1 Prelims: Ancient India — Indus Valley to Guptas"},
                    {"id": "m2-hi-01",  "label": "G1 Mains P2: Pre-Historic to Kushans"},
                    {"id": "p1-aph-01", "label": "G2 Paper 1: Pre-historic Cultures & Early Dynasties"}],
    "scr-hist-02": [{"id": "pre-ha-03", "label": "G1 Prelims: Medieval India"},
                    {"id": "pre-ha-04", "label": "G1 Prelims: Europeans in India"},
                    {"id": "m2-hi-02",  "label": "G1 Mains P2: South Indian Dynasties to Delhi Sultanate"},
                    {"id": "m2-hi-03",  "label": "G1 Mains P2: Mughals, Marathas & Europeans"},
                    {"id": "p1-aph-02", "label": "G2 Paper 1: Dynasties of 11th–16th Century AD"}],
    "scr-hist-03": [{"id": "pre-ha-05", "label": "G1 Prelims: 1857 & Reform Movements"},
                    {"id": "pre-ha-06", "label": "G1 Prelims: Gandhi, Independence & Post-Independence"},
                    {"id": "m2-hi-04",  "label": "G1 Mains P2: British Rule, 1857 & Reform Movements"},
                    {"id": "m2-hi-05",  "label": "G1 Mains P2: Indian Nationalism & Independence"},
                    {"id": "p1-aph-03", "label": "G2 Paper 1: Advent of Europeans to Independence"}],

    # G1 Mains Paper 2 — History of India ↔ G2 Screening + G2 Paper 1 AP History
    "m2-hi-01": [{"id": "cg-prehistoric-culture", "label": "Focused: Pre-Historic Cultures of India"},
                 {"id": "pre-ha-01",  "label": "G1 Prelims: Ancient India — Indus Valley to Guptas"},
                 {"id": "scr-hist-01","label": "G2 Screening: Ancient India"},
                 {"id": "p1-aph-01",  "label": "G2 Paper 1: Pre-historic Cultures & Early Dynasties"}],
    "m2-hi-02": [{"id": "pre-ha-02",  "label": "G1 Prelims: South Indian Dynasties"},
                 {"id": "pre-ha-03",  "label": "G1 Prelims: Medieval India"},
                 {"id": "scr-hist-02","label": "G2 Screening: Medieval India"},
                 {"id": "p1-aph-02",  "label": "G2 Paper 1: Dynasties of 11th–16th Century"}],
    "m2-hi-03": [{"id": "pre-ha-03",  "label": "G1 Prelims: Medieval India"},
                 {"id": "pre-ha-04",  "label": "G1 Prelims: Europeans in India"},
                 {"id": "scr-hist-02","label": "G2 Screening: Medieval India"},
                 {"id": "p1-aph-03",  "label": "G2 Paper 1: Advent of Europeans to Independence"}],
    "m2-hi-04": [{"id": "pre-ha-05",  "label": "G1 Prelims: 1857 & Reform Movements"},
                 {"id": "scr-hist-03","label": "G2 Screening: Modern India"},
                 {"id": "p1-aph-03",  "label": "G2 Paper 1: Advent of Europeans to Independence"}],
    "m2-hi-05": [{"id": "pre-ha-06",  "label": "G1 Prelims: Gandhi, Independence & Post-Independence"},
                 {"id": "scr-hist-03","label": "G2 Screening: Modern India"},
                 {"id": "p1-aph-03",  "label": "G2 Paper 1: Advent of Europeans to Independence"}],

    # Ancient History CG-specific notes → exam topic cross-links
    "cg-prehistoric-culture":  [{"id": "p1-aph-01",  "label": "G2 Paper 1: Pre-historic Cultures & Early Dynasties"},
                                 {"id": "m2-hi-01",   "label": "G1 Mains P2: Pre-Historic to Kushans"}],
    "cg-harappan-civilization":[{"id": "pre-ha-01",  "label": "G1 Prelims: Ancient India — Indus Valley to Guptas"},
                                 {"id": "scr-hist-01","label": "G2 Screening: Ancient India"}],
    "cg-vedic-age":            [{"id": "scr-hist-01","label": "G2 Screening: Ancient India"},
                                 {"id": "m2-hi-01",   "label": "G1 Mains P2: Pre-Historic to Kushans"}],
    "cg-mahajanapadas":        [{"id": "scr-hist-01","label": "G2 Screening: Ancient India"},
                                 {"id": "m2-hi-01",   "label": "G1 Mains P2: Pre-Historic to Kushans"}],

    # G1 Mains Paper 2 — AP History ↔ G2 Paper 1 AP History (STRONGEST OVERLAP)
    "m2-ap-01": [{"id": "p1-aph-01", "label": "G2 Paper 1: Pre-historic Cultures & Early Dynasties"},
                 {"id": "scr-hist-01","label": "G2 Screening: Ancient India"}],
    "m2-ap-02": [{"id": "p1-aph-02", "label": "G2 Paper 1: Dynasties of 11th–16th Century AD"}],
    "m2-ap-03": [{"id": "p1-aph-03", "label": "G2 Paper 1: Advent of Europeans to Independence"},
                 {"id": "scr-hist-03","label": "G2 Screening: Modern India"}],
    "m2-ap-04": [{"id": "p1-aph-04", "label": "G2 Paper 1: Andhra Movement & Formation of Andhra State"}],
    "m2-ap-05": [{"id": "p1-aph-05", "label": "G2 Paper 1: Formation of Andhra Pradesh (1956–2014)"}],

    # G2 Paper 1 AP History ↔ G1 Mains AP History (STRONGEST OVERLAP — near identical)
    "p1-aph-01": [{"id": "cg-prehistoric-culture", "label": "Focused: Pre-Historic Cultures of India"},
                  {"id": "m2-ap-01",  "label": "G1 Mains P2: Ancient Andhra"},
                  {"id": "m2-hi-01",  "label": "G1 Mains P2: Pre-Historic to Kushans"},
                  {"id": "scr-hist-01","label": "G2 Screening: Ancient India"}],
    "p1-aph-02": [{"id": "m2-ap-02",  "label": "G1 Mains P2: Medieval Andhra (1000–1565 AD)"},
                  {"id": "scr-hist-02","label": "G2 Screening: Medieval India"}],
    "p1-aph-03": [{"id": "m2-ap-03",  "label": "G1 Mains P2: Modern Andhra — Social Awakening"},
                  {"id": "m2-hi-04",  "label": "G1 Mains P2: British Rule, 1857 & Reform"},
                  {"id": "scr-hist-03","label": "G2 Screening: Modern India"}],
    "p1-aph-04": [{"id": "m2-ap-04",  "label": "G1 Mains P2: Andhra Movement & State Formation"}],
    "p1-aph-05": [{"id": "m2-ap-05",  "label": "G1 Mains P2: AP 1956–2014 & Bifurcation"}],

    # ── GEOGRAPHY ───────────────────────────────────────────────────────────

    # G1 Prelims Geography ↔ G2 Screening + G1 Mains Paper 2 Geography
    "pre-ge-01": [{"id": "scr-geo-01", "label": "G2 Screening: General & Physical Geography"},
                  {"id": "m2-ge-01",   "label": "G1 Mains P2: Physical Features & Resources"}],
    "pre-ge-02": [{"id": "scr-geo-01", "label": "G2 Screening: General & Physical Geography"},
                  {"id": "m2-ge-01",   "label": "G1 Mains P2: Physical Features & Resources"}],
    "pre-ge-03": [{"id": "scr-geo-03", "label": "G2 Screening: Human Geography of India & AP"},
                  {"id": "m2-ge-03",   "label": "G1 Mains P2: Social & Faunal-Floral Geography"}],
    "pre-ge-04": [{"id": "scr-geo-02", "label": "G2 Screening: Economic Geography of India & AP"},
                  {"id": "m2-ge-02",   "label": "G1 Mains P2: Economic Geography"}],

    # G2 Screening Geography ↔ G1 Prelims + G1 Mains
    "scr-geo-01": [{"id": "pre-ge-01", "label": "G1 Prelims: General & Physical Geography"},
                   {"id": "pre-ge-02", "label": "G1 Prelims: Physical Features — India & AP"},
                   {"id": "m2-ge-01",  "label": "G1 Mains P2: Physical Features & Resources"}],
    "scr-geo-02": [{"id": "pre-ge-04", "label": "G1 Prelims: Economic Geography"},
                   {"id": "m2-ge-02",  "label": "G1 Mains P2: Economic Geography"}],
    "scr-geo-03": [{"id": "pre-ge-03", "label": "G1 Prelims: Social & Human Geography"},
                   {"id": "m2-ge-03",  "label": "G1 Mains P2: Social & Faunal-Floral Geography"}],

    # G1 Mains Paper 2 Geography ↔ G2 Screening
    "m2-ge-01": [{"id": "pre-ge-01",  "label": "G1 Prelims: General & Physical Geography"},
                 {"id": "pre-ge-02",  "label": "G1 Prelims: Physical Features — India & AP"},
                 {"id": "scr-geo-01", "label": "G2 Screening: General & Physical Geography"}],
    "m2-ge-02": [{"id": "pre-ge-04",  "label": "G1 Prelims: Economic Geography"},
                 {"id": "scr-geo-02", "label": "G2 Screening: Economic Geography"}],
    "m2-ge-03": [{"id": "pre-ge-03",  "label": "G1 Prelims: Social & Human Geography"},
                 {"id": "scr-geo-03", "label": "G2 Screening: Human Geography"}],
    "m2-ge-04": [{"id": "scr-geo-01", "label": "G2 Screening: General & Physical Geography"}],

    # ── POLITY / CONSTITUTION ────────────────────────────────────────────────

    # G1 Prelims Polity ↔ G2 Paper 1 Constitution + G1 Mains Paper 3 Polity
    "pre-cp-01": [{"id": "p1-con-01", "label": "G2 Paper 1: Nature & Features of the Constitution"},
                  {"id": "m3-pc-01",  "label": "G1 Mains P3: Indian Constitution — Salient Features"}],
    "pre-cp-02": [{"id": "p1-con-02", "label": "G2 Paper 1: Structure & Functions of Indian Government"},
                  {"id": "p1-con-03", "label": "G2 Paper 1: Distribution of Powers — Union & States"},
                  {"id": "m3-pc-02",  "label": "G1 Mains P3: Federal Structure & Distribution of Powers"}],
    "pre-cp-03": [{"id": "p1-con-03", "label": "G2 Paper 1: Distribution of Powers — Union & States"},
                  {"id": "m3-pc-03",  "label": "G1 Mains P3: Local Governance & Constitutional Authorities"}],
    "pre-cp-04": [{"id": "m3-pa-03",  "label": "G1 Mains P3: Statutory, Regulatory Bodies & Civil Services"}],
    "pre-cp-05": [{"id": "m3-et-01",  "label": "G1 Mains P3: Ethics & Human Interface"},
                  {"id": "m3-et-02",  "label": "G1 Mains P3: Human Values, Attitude & Emotional Intelligence"}],
    "pre-cp-06": [{"id": "p1-con-04", "label": "G2 Paper 1: Centre–State Relations & Elections"}],

    # G2 Paper 1 Constitution ↔ G1 Prelims + G1 Mains Paper 3
    "p1-con-01": [{"id": "pre-cp-01", "label": "G1 Prelims: Indian Constitution — Evolution & Features"},
                  {"id": "m3-pc-01",  "label": "G1 Mains P3: Indian Constitution — Salient Features"}],
    "p1-con-02": [{"id": "pre-cp-02", "label": "G1 Prelims: Union, States & Federal Structure"},
                  {"id": "m3-pc-04",  "label": "G1 Mains P3: Parliament & State Legislatures"}],
    "p1-con-03": [{"id": "pre-cp-02", "label": "G1 Prelims: Union, States & Federal Structure"},
                  {"id": "pre-cp-03", "label": "G1 Prelims: Constitutional Authorities & Governance"},
                  {"id": "m3-pc-02",  "label": "G1 Mains P3: Federal Structure & Distribution of Powers"},
                  {"id": "m3-pc-03",  "label": "G1 Mains P3: Local Governance & Constitutional Authorities"}],
    "p1-con-04": [{"id": "pre-cp-06", "label": "G1 Prelims: India's Foreign Policy & IR"},
                  {"id": "m3-pc-02",  "label": "G1 Mains P3: Federal Structure & Distribution of Powers"}],
    "p1-con-05": [{"id": "m3-pc-03",  "label": "G1 Mains P3: Local Governance & Constitutional Authorities"}],

    # G1 Mains Paper 3 Polity ↔ G1 Prelims + G2 Paper 1 Constitution
    "m3-pc-01": [{"id": "pre-cp-01", "label": "G1 Prelims: Indian Constitution — Evolution & Features"},
                 {"id": "p1-con-01", "label": "G2 Paper 1: Nature & Features of the Constitution"}],
    "m3-pc-02": [{"id": "pre-cp-02", "label": "G1 Prelims: Union, States & Federal Structure"},
                 {"id": "p1-con-03", "label": "G2 Paper 1: Distribution of Powers — Union & States"},
                 {"id": "p1-con-04", "label": "G2 Paper 1: Centre–State Relations & Elections"}],
    "m3-pc-03": [{"id": "pre-cp-03", "label": "G1 Prelims: Constitutional Authorities & Governance"},
                 {"id": "p1-con-03", "label": "G2 Paper 1: Distribution of Powers — Union & States"},
                 {"id": "p1-con-05", "label": "G2 Paper 1: Decentralisation & Panchayati Raj"}],
    "m3-pc-04": [{"id": "p1-con-02", "label": "G2 Paper 1: Structure & Functions of Indian Government"}],
    "m3-pc-05": [{"id": "p1-con-03", "label": "G2 Paper 1: Distribution of Powers — Union & States"}],

    # ── ECONOMY ─────────────────────────────────────────────────────────────

    # G1 Prelims Economy ↔ G2 Paper 2 Economy + G1 Mains Paper 4
    "pre-ec-01": [{"id": "p2-eco-01", "label": "G2 Paper 2: Economic Structure & Planning"},
                  {"id": "m4-ec-01",  "label": "G1 Mains P4: Major Challenges of Indian Economy"},
                  {"id": "m4-ec-04",  "label": "G1 Mains P4: Inclusive Growth"}],
    "pre-ec-02": [{"id": "p2-eco-01", "label": "G2 Paper 2: Economic Structure & Planning"},
                  {"id": "m4-ec-04",  "label": "G1 Mains P4: Inclusive Growth"}],
    "pre-ec-03": [{"id": "p2-eco-03", "label": "G2 Paper 2: Agriculture, Industry & Services"},
                  {"id": "m4-ec-05",  "label": "G1 Mains P4: Agricultural Development"},
                  {"id": "m4-ec-06",  "label": "G1 Mains P4: Industrial Development & Policy"}],
    "pre-ec-04": [{"id": "p2-eco-02", "label": "G2 Paper 2: Money, Banking, Public Finance & Foreign Trade"},
                  {"id": "m4-ec-02",  "label": "G1 Mains P4: Resource Mobilization in Indian Economy"},
                  {"id": "m4-ec-03",  "label": "G1 Mains P4: Government Budgeting"}],
    "pre-ec-05": [{"id": "p2-eco-04", "label": "G2 Paper 2: AP Economy & Public Finance"},
                  {"id": "p2-eco-05", "label": "G2 Paper 2: AP Agriculture, Industry & Services"},
                  {"id": "m4-ap-01",  "label": "G1 Mains P4: Resource Mobilization in AP"},
                  {"id": "m4-ap-02",  "label": "G1 Mains P4: Government Budgeting in AP"},
                  {"id": "m4-ap-03",  "label": "G1 Mains P4: Agricultural Development in AP"},
                  {"id": "m4-ap-04",  "label": "G1 Mains P4: Industrial Policy of AP"}],

    # G2 Paper 2 Economy ↔ G1 Prelims + G1 Mains Paper 4
    "p2-eco-01": [{"id": "pre-ec-01", "label": "G1 Prelims: Indian Economy Basics & Planning"},
                  {"id": "pre-ec-02", "label": "G1 Prelims: National Income, Poverty & Employment"},
                  {"id": "m4-ec-01",  "label": "G1 Mains P4: Major Challenges of Indian Economy"},
                  {"id": "m4-ec-04",  "label": "G1 Mains P4: Inclusive Growth"}],
    "p2-eco-02": [{"id": "pre-ec-04", "label": "G1 Prelims: Financial Institutions & Fiscal Policy"},
                  {"id": "m4-ec-02",  "label": "G1 Mains P4: Resource Mobilization in Indian Economy"},
                  {"id": "m4-ec-03",  "label": "G1 Mains P4: Government Budgeting"}],
    "p2-eco-03": [{"id": "pre-ec-03", "label": "G1 Prelims: Agriculture, Industry & Economic Reforms"},
                  {"id": "m4-ec-05",  "label": "G1 Mains P4: Agricultural Development"},
                  {"id": "m4-ec-06",  "label": "G1 Mains P4: Industrial Development & Policy"}],
    "p2-eco-04": [{"id": "pre-ec-05", "label": "G1 Prelims: Andhra Pradesh Economy"},
                  {"id": "m4-ap-01",  "label": "G1 Mains P4: Resource Mobilization in AP"},
                  {"id": "m4-ap-02",  "label": "G1 Mains P4: Government Budgeting in AP"}],
    "p2-eco-05": [{"id": "pre-ec-05", "label": "G1 Prelims: Andhra Pradesh Economy"},
                  {"id": "m4-ap-03",  "label": "G1 Mains P4: Agricultural Development in AP"},
                  {"id": "m4-ap-04",  "label": "G1 Mains P4: Industrial Policy of AP"},
                  {"id": "m4-ap-05",  "label": "G1 Mains P4: Infrastructure Development in AP"}],

    # G1 Mains Paper 4 ↔ G1 Prelims + G2 Paper 2 Economy
    "m4-ec-01": [{"id": "pre-ec-01", "label": "G1 Prelims: Indian Economy Basics & Planning"},
                 {"id": "p2-eco-01", "label": "G2 Paper 2: Economic Structure & Planning"}],
    "m4-ec-02": [{"id": "pre-ec-04", "label": "G1 Prelims: Financial Institutions & Fiscal Policy"},
                 {"id": "p2-eco-02", "label": "G2 Paper 2: Money, Banking, Public Finance & Foreign Trade"}],
    "m4-ec-03": [{"id": "pre-ec-04", "label": "G1 Prelims: Financial Institutions & Fiscal Policy"},
                 {"id": "p2-eco-02", "label": "G2 Paper 2: Money, Banking, Public Finance & Foreign Trade"}],
    "m4-ec-04": [{"id": "pre-ec-01", "label": "G1 Prelims: Indian Economy Basics & Planning"},
                 {"id": "pre-ec-02", "label": "G1 Prelims: National Income, Poverty & Employment"},
                 {"id": "p2-eco-01", "label": "G2 Paper 2: Economic Structure & Planning"}],
    "m4-ec-05": [{"id": "pre-ec-03", "label": "G1 Prelims: Agriculture, Industry & Economic Reforms"},
                 {"id": "p2-eco-03", "label": "G2 Paper 2: Agriculture, Industry & Services"}],
    "m4-ec-06": [{"id": "pre-ec-03", "label": "G1 Prelims: Agriculture, Industry & Economic Reforms"},
                 {"id": "p2-eco-03", "label": "G2 Paper 2: Agriculture, Industry & Services"}],
    "m4-ec-07": [{"id": "m4-ap-05",  "label": "G1 Mains P4: Infrastructure in AP"},
                 {"id": "p2-eco-04", "label": "G2 Paper 2: AP Economy & Public Finance"}],
    "m4-ap-01": [{"id": "pre-ec-05", "label": "G1 Prelims: Andhra Pradesh Economy"},
                 {"id": "p2-eco-04", "label": "G2 Paper 2: AP Economy & Public Finance"}],
    "m4-ap-02": [{"id": "pre-ec-05", "label": "G1 Prelims: Andhra Pradesh Economy"},
                 {"id": "p2-eco-04", "label": "G2 Paper 2: AP Economy & Public Finance"}],
    "m4-ap-03": [{"id": "pre-ec-05", "label": "G1 Prelims: Andhra Pradesh Economy"},
                 {"id": "p2-eco-05", "label": "G2 Paper 2: AP Agriculture, Industry & Services"}],
    "m4-ap-04": [{"id": "pre-ec-05", "label": "G1 Prelims: Andhra Pradesh Economy"},
                 {"id": "p2-eco-05", "label": "G2 Paper 2: AP Agriculture, Industry & Services"}],
    "m4-ap-05": [{"id": "pre-ec-05", "label": "G1 Prelims: Andhra Pradesh Economy"},
                 {"id": "p2-eco-05", "label": "G2 Paper 2: AP Agriculture, Industry & Services"},
                 {"id": "m4-ec-07",  "label": "G1 Mains P4: Infrastructure in India"}],

    # ── SCIENCE & TECHNOLOGY ────────────────────────────────────────────────

    # G1 Prelims S&T ↔ G2 Paper 2 S&T + G1 Mains Paper 5
    "pre-st-01": [{"id": "p2-sci-01", "label": "G2 Paper 2: Technology Missions, Policies & Applications"},
                  {"id": "p2-sci-03", "label": "G2 Paper 2: Ecosystem & Biodiversity"},
                  {"id": "p2-sci-05", "label": "G2 Paper 2: Environment & Health"},
                  {"id": "m5-st-01",  "label": "G1 Mains P5: Integration of S&T for Human Life"},
                  {"id": "m5-st-03",  "label": "G1 Mains P5: Indian Space Programme & DRDO"}],

    # G2 Paper 2 Science ↔ G1 Prelims + G1 Mains Paper 5
    "p2-sci-01": [{"id": "pre-st-01", "label": "G1 Prelims: Science & Technology"},
                  {"id": "m5-st-01",  "label": "G1 Mains P5: Integration of S&T for Human Life"},
                  {"id": "m5-st-02",  "label": "G1 Mains P5: ICT, E-Governance & Cyber Security"},
                  {"id": "m5-st-03",  "label": "G1 Mains P5: Indian Space Programme & DRDO"},
                  {"id": "m5-st-04",  "label": "G1 Mains P5: Energy & Nuclear Policy"}],
    "p2-sci-02": [{"id": "pre-st-01", "label": "G1 Prelims: Science & Technology"},
                  {"id": "m5-st-04",  "label": "G1 Mains P5: Energy & Nuclear Policy"}],
    "p2-sci-03": [{"id": "pre-st-01", "label": "G1 Prelims: Science & Technology"},
                  {"id": "m5-st-05",  "label": "G1 Mains P5: Biotechnology & Nanotechnology"}],
    "p2-sci-04": [{"id": "m5-st-05",  "label": "G1 Mains P5: Biotechnology & Nanotechnology"}],
    "p2-sci-05": [{"id": "pre-st-01", "label": "G1 Prelims: Science & Technology"}],

    # G1 Mains Paper 5 S&T ↔ G1 Prelims + G2 Paper 2 S&T
    "m5-st-01": [{"id": "pre-st-01",  "label": "G1 Prelims: Science & Technology"},
                 {"id": "p2-sci-01",  "label": "G2 Paper 2: Technology Missions, Policies & Applications"}],
    "m5-st-02": [{"id": "pre-st-01",  "label": "G1 Prelims: Science & Technology"},
                 {"id": "p2-sci-01",  "label": "G2 Paper 2: Technology Missions, Policies & Applications"}],
    "m5-st-03": [{"id": "pre-st-01",  "label": "G1 Prelims: Science & Technology"},
                 {"id": "p2-sci-01",  "label": "G2 Paper 2: Technology Missions, Policies & Applications"}],
    "m5-st-04": [{"id": "pre-st-01",  "label": "G1 Prelims: Science & Technology"},
                 {"id": "p2-sci-01",  "label": "G2 Paper 2: Technology Missions, Policies & Applications"},
                 {"id": "p2-sci-02",  "label": "G2 Paper 2: Energy Management"}],
    "m5-st-05": [{"id": "p2-sci-03",  "label": "G2 Paper 2: Ecosystem & Biodiversity"},
                 {"id": "p2-sci-04",  "label": "G2 Paper 2: Waste Management & Pollution Control"}],

    # ── MENTAL ABILITY ──────────────────────────────────────────────────────

    "pre-ma-01": [{"id": "scr-ma-01", "label": "G2 Screening: Logical Reasoning"}],
    "pre-ma-02": [{"id": "scr-ma-02", "label": "G2 Screening: Mental Ability"},
                  {"id": "scr-ma-03", "label": "G2 Screening: Basic Numeracy & Data Analysis"}],
    "pre-ma-03": [{"id": "m3-et-01",  "label": "G1 Mains P3: Ethics & Human Interface"},
                  {"id": "m3-et-02",  "label": "G1 Mains P3: Human Values, Attitude & Emotional Intelligence"}],
    "scr-ma-01": [{"id": "pre-ma-01", "label": "G1 Prelims: Reasoning & Analytical Ability"}],
    "scr-ma-02": [{"id": "pre-ma-02", "label": "G1 Prelims: Quantitative Aptitude"}],
    "scr-ma-03": [{"id": "pre-ma-02", "label": "G1 Prelims: Quantitative Aptitude"}],

    # ── CURRENT AFFAIRS ─────────────────────────────────────────────────────

    "pre-st-02": [{"id": "scr-ca-01", "label": "G2 Screening: Current Affairs"},
                  {"id": "m1-ge-01",  "label": "G1 Mains P1: General Essay (Current Affairs)"}],
    "scr-ca-01": [{"id": "pre-st-02", "label": "G1 Prelims: Current Events"},
                  {"id": "m1-ge-01",  "label": "G1 Mains P1: General Essay (Current Affairs)"}],
    "m1-ge-01":  [{"id": "pre-st-02", "label": "G1 Prelims: Current Events"},
                  {"id": "scr-ca-01", "label": "G2 Screening: Current Affairs"}],

    # ── G1 MAINS PAPER 3 ETHICS ↔ G1 PRELIMS ───────────────────────────────

    "m3-et-01": [{"id": "pre-cp-05",  "label": "G1 Prelims: Rights Issues"},
                 {"id": "pre-ma-03",  "label": "G1 Prelims: Emotional & Social Intelligence"}],
    "m3-et-02": [{"id": "pre-cp-05",  "label": "G1 Prelims: Rights Issues"},
                 {"id": "pre-ma-03",  "label": "G1 Prelims: Emotional & Social Intelligence"}],
    "m3-pa-03": [{"id": "pre-cp-04",  "label": "G1 Prelims: LPG Impact & Regulatory Bodies"}],

    # ── G2 SCREENING SOCIETY ↔ G1 MAINS ────────────────────────────────────

    "scr-soc-01": [{"id": "m3-et-01",  "label": "G1 Mains P3: Ethics & Human Interface"}],
    "scr-soc-02": [{"id": "m3-et-01",  "label": "G1 Mains P3: Ethics & Human Interface"},
                   {"id": "m3-et-02",  "label": "G1 Mains P3: Human Values, Attitude & Emotional Intelligence"}],
    "scr-soc-03": [{"id": "pre-cp-05", "label": "G1 Prelims: Rights Issues"},
                   {"id": "m3-pa-02",  "label": "G1 Mains P3: Government Policies, Civil Society & NGOs"}],
}


# ---------------------------------------------------------------------------
# Aptitude & Reasoning — aggregated from G1 Prelims + G2 Screening
# ---------------------------------------------------------------------------

APT_STRUCTURE = {
    "sections": [
        {
            "title": "Reasoning & Mental Ability",
            "topics": [
                {
                    "id": "apt-r-01",
                    "exam": "G2 Screening",
                    "title": "Logical Reasoning",
                    "points": [
                        "Deductive, Inductive and Abductive Reasoning",
                        "Statement and Assumptions",
                        "Statement and Argument",
                        "Statement and Conclusion",
                        "Statement and Courses of Action",
                    ],
                },
                {
                    "id": "apt-r-02",
                    "exam": "G2 Screening",
                    "title": "Mental Ability",
                    "points": [
                        "Number Series and Letter Series",
                        "Odd Man Out",
                        "Coding and Decoding",
                        "Problems relating to Relations",
                        "Shapes and their Sub-Sections",
                    ],
                },
                {
                    "id": "apt-r-03",
                    "exam": "G1 Prelims",
                    "title": "Reasoning & Analytical Ability",
                    "points": [
                        "Logical Reasoning and Analytical Ability",
                        "Number Series and Coding-Decoding",
                        "Problems Related to Relations",
                        "Shapes and their Sub-Sections, Venn Diagram",
                        "Problems based on Clocks, Calendar and Age",
                    ],
                },
                {
                    "id": "apt-r-04",
                    "exam": "G1 Prelims",
                    "title": "Emotional & Social Intelligence",
                    "points": [
                        "Emotional Intelligence: Understanding and Analyzing Emotions, Dimensions of Emotional Intelligence, Coping with Emotions, Empathy and Coping with Stress",
                        "Social Intelligence, Interpersonal Skills, Decision Making, Critical Thinking, Problem Solving and Assessment of Personality",
                    ],
                },
            ],
        },
        {
            "title": "Quantitative Aptitude",
            "topics": [
                {
                    "id": "apt-q-01",
                    "exam": "G2 Screening",
                    "title": "Basic Numeracy & Data Analysis",
                    "points": [
                        "Number System and Order of Magnitude",
                        "Averages, Ratio and Proportion, Percentage",
                        "Simple and Compound Interest",
                        "Time and Work; Time and Distance",
                        "Data Analysis: Tables, Bar Diagram, Line Graph, Pie-chart",
                    ],
                },
                {
                    "id": "apt-q-02",
                    "exam": "G1 Prelims",
                    "title": "Quantitative Aptitude",
                    "points": [
                        "Number System and Order of Magnitude",
                        "Ratio, Proportion and Variation",
                        "Central Tendencies — Mean, Median, Mode (including Weighted Mean)",
                        "Power and Exponent, Square, Square Root, Cube Root, HCF and LCM",
                        "Percentage, Simple and Compound Interest, Profit and Loss",
                        "Time and Work; Time and Distance; Speed and Distance",
                        "Area and Perimeter of Simple Geometrical Shapes; Volume and Surface Area of Sphere, Cone, Cylinder, Cubes and Cuboids",
                        "Lines, Angles and Common Geometrical Figures; Properties of Triangles, Quadrilateral, Rectangle, Parallelogram and Rhombus",
                        "Introduction to Algebra — BODMAS, Simplification",
                        "Data Interpretation, Data Analysis, Data Sufficiency and Probability",
                    ],
                },
            ],
        },
    ],
}

# ── Topic slug index — maps internal IDs to clean URL slugs ──────────────────
def _slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', '-', s.strip())
    s = re.sub(r'-+', '-', s)
    return s.strip('-')

def _build_topic_index() -> dict:
    index: dict = {}
    seen_slugs: dict = {}

    def _add(tid: str, title: str):
        if tid in index:
            return
        base = _slugify(title)
        slug = base
        if slug in seen_slugs and seen_slugs[slug] != tid:
            slug = f"{base}-{_slugify(tid)}"
        seen_slugs[slug] = tid
        index[tid] = {"title": title, "slug": slug}

    for stage in G2_STRUCTURE.values():
        for sec in stage["sections"]:
            for t in sec["topics"]:
                _add(t["id"], t["title"])

    for stage in G1_STRUCTURE.values():
        for sec in stage["sections"]:
            for t in sec["topics"]:
                _add(t["id"], t["title"])

    for sec in APT_STRUCTURE["sections"]:
        for t in sec["topics"]:
            _add(t["id"], t["title"])

    return index

TOPIC_INDEX = _build_topic_index()
SLUG_TO_ID  = {v["slug"]: k for k, v in TOPIC_INDEX.items()}


async def aptitude(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "aptitude.html", {
        "structure": APT_STRUCTURE,
        "structure_json": json.dumps(APT_STRUCTURE),
        "current_user": user,
        "user_id": user["id"] if user else None,
    })


# ---------------------------------------------------------------------------
# Telugu — Bilingual Learning + APPSC Paper
# ---------------------------------------------------------------------------

TELUGU_STRUCTURE = {
    "basics": {
        "label": "Learn Telugu",
        "subtitle": "Start from Scratch",
        "sections": {
            "script": {
                "label": "Telugu Script",
                "sub": "అక్షరమాల — The Alphabet",
                "topics": {
                    "vowels": {
                        "title": "Vowels (అచ్చులు)",
                        "meta": "16 Vowels • Telugu Basics",
                        "points": [
                            "అ (a) — short 'a', as in 'about'",
                            "ఆ (aa) — long 'a', as in 'father'",
                            "ఇ (i) — short 'i', as in 'pin'",
                            "ఈ (ii) — long 'i', as in 'see'",
                            "ఉ (u) — short 'u', as in 'put'",
                            "ఊ (uu) — long 'u', as in 'food'",
                            "ఋ (ru) — retroflex vowel, Sanskrit origin",
                            "ఎ (e) — short 'e', as in 'bet'",
                            "ఏ (ee) — long 'e', as in 'late'",
                            "ఐ (ai) — diphthong, as in 'high'",
                            "ఒ (o) — short 'o', as in 'hot'",
                            "ఓ (oo) — long 'o', as in 'go'",
                            "ఔ (au) — diphthong, as in 'out'",
                            "అం (am) — anusvara, nasal sound",
                            "అః (aha) — visarga, aspirated sound",
                        ],
                    },
                    "consonants_ka": {
                        "title": "Velar Group — కంఠ్యాలు (K sounds)",
                        "meta": "Consonants • Group I of 7",
                        "points": [
                            "క (ka) — as in 'k' in 'kite' | కమలం = lotus",
                            "ఖ (kha) — aspirated 'k' | ఖాళీ = empty",
                            "గ (ga) — as in 'g' in 'go' | గమనం = movement",
                            "ఘ (gha) — aspirated 'g' | ఘనత = greatness",
                            "ఙ (nga) — nasal 'ng', as in 'sing' (rare, in conjuncts)",
                        ],
                    },
                    "consonants_cha": {
                        "title": "Palatal Group — తాలవ్యాలు (Ch sounds)",
                        "meta": "Consonants • Group II of 7",
                        "points": [
                            "చ (cha) — as in 'ch' in 'chair' | చంద్రుడు = moon",
                            "ఛ (chha) — aspirated 'ch' | ఛత్రం = umbrella",
                            "జ (ja) — as in 'j' in 'jungle' | జలం = water",
                            "ఝ (jha) — aspirated 'j' | ఝరి = waterfall",
                            "ఞ (nya) — palatal nasal, as in 'ny' (rare, in conjuncts)",
                        ],
                    },
                    "consonants_ta_retro": {
                        "title": "Retroflex Group — మూర్ధన్యాలు (T retroflex)",
                        "meta": "Consonants • Group 3 of 7",
                        "points": [
                            "ట (Ta) — retroflex 't', tongue curls back | టైమ్ = time",
                            "ఠ (Tha) — aspirated retroflex 't' | ఠీవి = dignity",
                            "డ (Da) — retroflex 'd' | డబ్బు = money",
                            "ఢ (Dha) — aspirated retroflex 'd' | ఢంకా = drum",
                            "ణ (Na) — retroflex nasal | ణకారం = the letter ణ",
                        ],
                    },
                    "consonants_ta_dental": {
                        "title": "Dental Group — దంత్యాలు (T dental)",
                        "meta": "Consonants • Group 4 of 7",
                        "points": [
                            "త (ta) — dental 't', tongue at teeth | తల = head",
                            "థ (tha) — aspirated dental 't' | థాలీ = plate",
                            "ద (da) — dental 'd' | దారి = path/road",
                            "ధ (dha) — aspirated dental 'd' | ధనం = money/wealth",
                            "న (na) — dental nasal | నది = river",
                        ],
                    },
                    "consonants_pa": {
                        "title": "Labial Group — ఓష్ఠ్యాలు (P sounds)",
                        "meta": "Consonants • Group 5 of 7",
                        "points": [
                            "ప (pa) — as in 'p' in 'pen' | పాలు = milk",
                            "ఫ (pha) — aspirated 'p' | ఫలితం = result",
                            "బ (ba) — as in 'b' in 'bat' | బడి = school",
                            "భ (bha) — aspirated 'b' | భవనం = building",
                            "మ (ma) — as in 'm' in 'man' | మనసు = mind/heart",
                        ],
                    },
                    "consonants_semi": {
                        "title": "Semi-vowels & Sibilants (Y, R, L, V, S, H)",
                        "meta": "Consonants • Group 6 & 7 of 7",
                        "points": [
                            "య (ya) — as in 'y' in 'yes' | యువత = youth",
                            "ర (ra) — as in 'r' in 'run' | రాత్రి = night",
                            "ల (la) — as in 'l' in 'lake' | లోకం = world",
                            "వ (va) — as in 'v' in 'van' | వర్షం = rain",
                            "శ (sha) — palatal sibilant 'sh' | శాంతి = peace",
                            "ష (Sha) — retroflex sibilant | షడ్రసాలు = six tastes",
                            "స (sa) — as in 's' in 'sun' | సమయం = time",
                            "హ (ha) — as in 'h' in 'hat' | హృదయం = heart",
                            "ళ (Lla) — retroflex lateral, unique to Telugu | పళ్ళు = teeth",
                            "క్ష (ksha) — combined consonant | క్షమ = forgiveness",
                            "ఱ (rra) — rolled 'r', archaic form used in classical texts",
                        ],
                    },
                },
            },
            "numbers": {
                "label": "Numbers",
                "sub": "సంఖ్యలు — Count in Telugu",
                "topics": {
                    "numbers_0_10": {
                        "title": "Numbers 0–10 (సంఖ్యలు)",
                        "meta": "Basics • Telugu Numbers",
                        "points": [
                            "0 — సున్న (sunna)",
                            "1 — ఒకటి (okaTi)",
                            "2 — రెండు (reṃDu)",
                            "3 — మూడు (muuDu)",
                            "4 — నాలుగు (naalugu)",
                            "5 — అయిదు (ayidu)",
                            "6 — ఆరు (aaru)",
                            "7 — ఏడు (eeḍu)",
                            "8 — ఎనిమిది (enimidi)",
                            "9 — తొమ్మిది (tommidi)",
                            "10 — పది (padi)",
                        ],
                    },
                    "numbers_11_20": {
                        "title": "Numbers 11–20",
                        "meta": "Intermediate • Telugu Numbers",
                        "points": [
                            "11 — పదకొండు (padakonDu)",
                            "12 — పన్నెండు (panneṃDu)",
                            "13 — పదమూడు (padamuuDu)",
                            "14 — పదునాలుగు (padunaalugu)",
                            "15 — పదిహేను (padihenu)",
                            "16 — పదహారు (padahaaru)",
                            "17 — పదిహేడు (padiheeḍu)",
                            "18 — పదునెనిమిది (padunenmidi)",
                            "19 — పందొమ్మిది (pandommidi)",
                            "20 — ఇరవై (iravai)",
                        ],
                    },
                    "numbers_tens": {
                        "title": "Tens & Key Numbers",
                        "meta": "Advanced • Telugu Numbers",
                        "points": [
                            "30 — ముప్పై (muppai)",
                            "40 — నలభై (nalabhai)",
                            "50 — యాభై (yaabhai)",
                            "60 — అరవై (aravai)",
                            "70 — డెభ్భై (Debbhai)",
                            "80 — ఎనభై (enabhai)",
                            "90 — తొంభై (tombhai)",
                            "100 — వంద (vanda)",
                            "1,000 — వేయి (veeyi)",
                            "100,000 — లక్ష (laksha)",
                            "10,000,000 — కోటి (koti)",
                        ],
                    },
                },
            },
            "greetings": {
                "label": "Greetings & Phrases",
                "sub": "రోజువారీ మాటలు — Daily Conversation",
                "topics": {
                    "greetings_basic": {
                        "title": "Basic Greetings (శుభాకాంక్షలు)",
                        "meta": "Conversation • Daily Use",
                        "points": [
                            "నమస్కారం (Namaskaram) — Hello / Greetings (formal)",
                            "నమస్తే (Namaste) — Hello (slightly informal)",
                            "హాయ్ (Haay) — Hi (casual, modern)",
                            "శుభోదయం (Shubhodayam) — Good morning",
                            "శుభ సాయంత్రం (Shubha Sayantram) — Good evening",
                            "శుభ రాత్రి (Shubha Raatri) — Good night",
                            "వెళ్ళొస్తాను (Vellostaanu) — Goodbye (lit. I'll go and come back)",
                            "తర్వాత కలుద్దాం (Tarvaata kaluddaam) — See you later",
                        ],
                    },
                    "phrases_polite": {
                        "title": "Polite Expressions",
                        "meta": "Conversation • Politeness",
                        "points": [
                            "ధన్యవాదాలు (Dhanyavaadaalu) — Thank you",
                            "దయచేసి (Dayacheesi) — Please",
                            "క్షమించండి (Kshamincandi) — Sorry / Excuse me",
                            "సరే (Sare) — Okay / Alright",
                            "అవును (Avunu) — Yes",
                            "కాదు (Kaadu) — No",
                            "నాకు అర్థం కాలేదు (Naaku artham kaaledu) — I don't understand",
                            "మళ్ళీ చెప్పండి (Mallee cheppandi) — Please say it again",
                            "మీ పేరు ఏమిటి? (Mee peru emiti?) — What is your name?",
                            "నా పేరు ___ (Naa peru ___) — My name is ___",
                        ],
                    },
                    "phrases_daily": {
                        "title": "Daily Life Phrases",
                        "meta": "Conversation • Everyday",
                        "points": [
                            "బాగున్నారా? (Baagunnaara?) — How are you?",
                            "బాగున్నాను (Baagunnaanu) — I am well",
                            "నాకు ఆకలి వేస్తోంది (Naaku aakali veestundi) — I am hungry",
                            "నీళ్ళు ఇవ్వండి (Neellu ivvandi) — Please give water",
                            "ఇది ఎంత? (Idi enta?) — How much is this?",
                            "అక్కడ ఎలా వెళ్ళాలి? (Akkada elaa vellaali?) — How to go there?",
                            "సమయం ఎంత అయింది? (Samayam enta ayindi?) — What time is it?",
                            "నాకు సహాయం చేయండి (Naaku sahaayam cheyandi) — Please help me",
                        ],
                    },
                },
            },
            "days_months": {
                "label": "Days & Months",
                "sub": "వారాలు & నెలలు — Calendar Words",
                "topics": {
                    "days": {
                        "title": "Days of the Week (వారాలు)",
                        "meta": "Calendar • Days",
                        "points": [
                            "ఆదివారం (Aadivaram) — Sunday",
                            "సోమవారం (Somavaram) — Monday",
                            "మంగళవారం (Mangalavaram) — Tuesday",
                            "బుధవారం (Budhavaram) — Wednesday",
                            "గురువారం (Guruvaram) — Thursday",
                            "శుక్రవారం (Shukravaram) — Friday",
                            "శనివారం (Shanivaram) — Saturday",
                        ],
                    },
                    "months": {
                        "title": "English Months in Telugu (నెలలు)",
                        "meta": "Calendar • English Months",
                        "points": [
                            "జనవరి (Janavari) — January",
                            "ఫిబ్రవరి (Phibravari) — February",
                            "మార్చి (Maarchi) — March",
                            "ఏప్రిల్ (Eepril) — April",
                            "మే (Me) — May",
                            "జూన్ (Juun) — June",
                            "జూలై (Juulai) — July",
                            "ఆగస్టు (Aagustu) — August",
                            "సెప్టెంబర్ (Septambar) — September",
                            "అక్టోబర్ (Aktobar) — October",
                            "నవంబర్ (Navambar) — November",
                            "డిసెంబర్ (Disambar) — December",
                        ],
                    },
                    "telugu_months": {
                        "title": "Telugu Calendar Months (తెలుగు నెలలు)",
                        "meta": "Calendar • Telugu Months",
                        "points": [
                            "చైత్రం (Chaitram) — Mar–Apr | Telugu New Year (Ugadi) falls in this month",
                            "వైశాఖం (Vaishakham) — Apr–May",
                            "జ్యేష్ఠం (Jyeshtham) — May–Jun",
                            "ఆషాఢం (Aashadham) — Jun–Jul",
                            "శ్రావణం (Shravanam) — Jul–Aug | Raksha Bandhan, Varalakshmi Vratam",
                            "భాద్రపదం (Bhadrapadam) — Aug–Sep | Ganesh Chaturthi",
                            "ఆశ్వయుజం (Ashvayujam) — Sep–Oct | Navaratri, Dussehra",
                            "కార్తీకం (Kartikam) — Oct–Nov | Deepavali",
                            "మార్గశిరం (Margashiram) — Nov–Dec",
                            "పుష్యం (Pushyam) — Dec–Jan",
                            "మాఘం (Maagham) — Jan–Feb | Maha Shivaratri",
                            "ఫాల్గుణం (Phalgunam) — Feb–Mar | Holi",
                        ],
                    },
                },
            },
        },
    },
    "appsc": {
        "label": "APPSC Paper",
        "subtitle": "Telugu Paper for APPSC Exams",
        "sections": {
            "grammar": {
                "label": "Telugu Grammar",
                "sub": "వ్యాకరణం — High Weightage",
                "topics": {
                    "sandhi": {
                        "title": "సంధులు (Sandhi — Euphonic Combinations)",
                        "meta": "Grammar • Very High Weightage",
                        "points": [
                            "అకార సంధి — Combination of 'a' + 'a' = long 'aa' (e.g., రామ + అయ్య = రామయ్య)",
                            "ఇకార సంధి — Combinations involving 'i' sound",
                            "ఉకార సంధి — Combinations involving 'u' sound",
                            "యడాగమ సంధి — Insertion of 'y' as liaison consonant (e.g., రా + ఇ = రాయి)",
                            "తత్సమ సంధులు — Sandhi rules borrowed from Sanskrit (e.g., విద్యా + అలయం = విద్యాలయం)",
                            "గసడదవాదేశ సంధి — Substitution sandhi: first consonant of second word changes",
                            "ద్రుత ప్రకృతిక సంధి — Sandhi with short/dhruta words (ని, ఒ, etc.)",
                            "లోపసంధి — Elision sandhi: a vowel is dropped",
                            "ర్వాదేశ సంధి — Substitution by 'r'-sound",
                        ],
                    },
                    "samasa": {
                        "title": "సమాసాలు (Samasa — Compound Words)",
                        "meta": "Grammar • Very High Weightage",
                        "points": [
                            "తత్పురుష సమాసం — Determinative compound: second word is head (e.g., రాజభవనం = king's palace)",
                            "కర్మధారయ సమాసం — Appositional: both words refer to same thing (e.g., నీలకమలం = blue lotus)",
                            "ద్విగు సమాసం — Numeral compound: first word is number (e.g., త్రిలోకం = three worlds)",
                            "ద్వంద్వ సమాసం — Copulative 'and' compound (e.g., రాజరాణి = king and queen)",
                            "బహువ్రీహి సమాసం — Possessive: compound describes something else (e.g., నీలకంఠుడు = Shiva)",
                            "అవ్యయీభావ సమాసం — Adverbial compound (e.g., యథాశక్తి = as per ability)",
                            "నఞ్ సమాసం — Negative compound with 'a-' or 'an-' prefix (e.g., అన్యాయం = injustice)",
                        ],
                    },
                    "vibhakti": {
                        "title": "విభక్తులు (Vibhakti — Case Endings)",
                        "meta": "Grammar • Foundational",
                        "points": [
                            "ప్రథమా విభక్తి — Nominative (subject): -డు, -ము, -వు (రాముడు వెళ్ళాడు)",
                            "ద్వితీయా విభక్తి — Accusative (object): -ని, -ను (పుస్తకాన్ని చదివాను)",
                            "తృతీయా విభక్తి — Instrumental (by/with): -తో, -చేత (కలంతో రాశాను)",
                            "చతుర్థీ విభక్తి — Dative (for/to): -కు, -కి (అమ్మకు ఇచ్చాను)",
                            "పంచమీ విభక్తి — Ablative (from): -నుండి, -నుంచి (హైదరాబాదు నుండి వచ్చాను)",
                            "షష్ఠీ విభక్తి — Genitive (of): -యొక్క (రాముని యొక్క బాణం)",
                            "సప్తమీ విభక్తి — Locative (in/at): -లో, -న (గ్రామంలో ఉన్నాను)",
                            "సంబోధన విభక్తి — Vocative (O!/Hey!): -ఓ, -ఏ (రామా! ఓ కృష్ణా!)",
                        ],
                    },
                    "chandassu": {
                        "title": "ఛందస్సు (Chandassu — Prosody & Metres)",
                        "meta": "Grammar • Medium Weightage",
                        "points": [
                            "ఉత్పలమాల — 20-syllable metre; most popular in classical Telugu poetry",
                            "చంపకమాల — 21-syllable metre; common in ornate prabandhas",
                            "శార్దూలవిక్రీడితం — 19-syllable metre (gana-based, from Sanskrit)",
                            "మత్తేభవిక్రీడితం — 20-syllable metre",
                            "తేటగీతి — Native Telugu metre; used since ancient Nannaya period",
                            "ఆటవెలది — Shorter Telugu metre; used in folk and classical compositions",
                            "సీసపద్యం — Four-line metre with unique 'sisa' pattern",
                            "కందపద్యం — Quatrain metre; specific gana rules; very popular",
                        ],
                    },
                    "alankaras": {
                        "title": "అలంకారాలు (Alankaras — Figures of Speech)",
                        "meta": "Grammar • Medium Weightage",
                        "points": [
                            "ఉపమాలంకారం — Simile: comparison using 'like' or 'as' (వంటి, లాంటి)",
                            "రూపకాలంకారం — Metaphor: direct identification without 'like'",
                            "ఉత్ప్రేక్షాలంకారం — Fancy/Poetic fancy: imagining one thing as another",
                            "అతిశయోక్తి — Hyperbole: deliberate exaggeration for effect",
                            "యమకం — Repetition of same-sounding syllables with different meanings",
                            "అనుప్రాస — Alliteration: same consonant sound repeated at word-starts",
                            "శ్లేష — Pun: single expression with two different meanings",
                            "విరోధాభాస — Paradox: apparent contradiction that reveals truth",
                        ],
                    },
                },
            },
            "literature": {
                "label": "Telugu Literature",
                "sub": "సాహిత్యం — Periods & Works",
                "topics": {
                    "ancient": {
                        "title": "Ancient Period — నన్నయ నుండి (11th–14th Century)",
                        "meta": "Literature • Classical Era",
                        "points": [
                            "నన్నయ భట్టు (1022–1063) — First Telugu poet; translated Mahabharata (Adiparva + Sabhaparva)",
                            "తిక్కన సోమయాజి (1220–1300) — 'Ubhaya Kavi Mitra'; completed 15 parvas of Mahabharata",
                            "ఎఱ్ఱన (1280–1350) — Completed Aranyaparva; known for Raghavapandaviyam (dvyartha kavya)",
                            "ముగ్గురు కవులు — 'Kavitrayam' (Three Poets): Nannaya, Tikkana, Errana",
                            "పాల్కురికి సోమనాథుడు — Shaiva bhakti poet; Basavapurana in native Telugu metres",
                        ],
                    },
                    "vijayanagara": {
                        "title": "Vijayanagara Period (14th–16th Century)",
                        "meta": "Literature • Golden Age",
                        "points": [
                            "శ్రీనాథుడు (1379–1470) — 'Kavi Sarvabhouma'; Shringaranaishadha, Kasikhanda",
                            "పోతన (1450–1510) — Composed Bhagavatam in Telugu; rejected royal patronage for devotion",
                            "అష్టదిగ్గజాలు — Eight celebrated poets at court of Krishna Devaraya",
                            "కృష్ణదేవరాయలు (1509–1529) — Composed Amuktamalyada (the gem of Telugu kavya)",
                            "అల్లసాని పెద్దన — 'Andhra Kavita Pitamaha'; wrote Manucharitra (first Prabandha)",
                            "నంది తిమ్మన — Wrote Parijatapaharana; known as 'Mukku Timmana'",
                        ],
                    },
                    "modern": {
                        "title": "Modern Period (19th–20th Century)",
                        "meta": "Literature • Renaissance Era",
                        "points": [
                            "గురజాడ అప్పారావు (1862–1915) — Father of modern Telugu literature; Kanyasulkam (social play)",
                            "కందుకూరి వీరేశలింగం — Social reformer; wrote first Telugu novel Rajashekhara Charitra",
                            "విశ్వనాథ సత్యనారాయణ — Jnanpith Award winner (1970); Ramayana Kalpavrikshamu",
                            "శ్రీ శ్రీ (1910–1983) — 'Mahakavi'; Maha Prasthanam (revolutionary poetry)",
                            "జాషువా (1895–1971) — Dalit poet; Gabbilam, Firdausi — voice of the marginalized",
                            "దేవులపల్లి కృష్ణశాస్త్రి — Romantic lyricist; called 'Telugu Shelley'",
                        ],
                    },
                    "prabandhas": {
                        "title": "Important Prabandhas (ప్రబంధాలు)",
                        "meta": "Literature • Key Works",
                        "points": [
                            "మనుచరిత్ర — Allasani Peddana; first Telugu Prabandha; story of Manu and Varuthini",
                            "అముక్తమాల్యద — Krishna Devaraya; story of Andal (Godadevi); greatest Telugu kavya",
                        "రాఘవపాండవీయం — Errana; dvyartha kavya describing both Ramayana and Mahabharata simultaneously",
                            "కాళహస్తి మాహాత్మ్యం — Dhurjati; devotional Shaiva prabandha",
                            "పాండురంగ మాహాత్మ్యం — Tenali Ramakrishna; Vaishnava devotional work",
                            "కళాపూర్ణోదయం — Pingali Suranna; early realistic novel-like prabandha",
                        ],
                    },
                },
            },
            "essay": {
                "label": "General Essay",
                "sub": "వ్యాస రచన — Writing Skills",
                "topics": {
                    "essay_structure": {
                        "title": "Essay Structure & Format (నిర్మాణం)",
                        "meta": "Essay • Writing Technique",
                        "points": [
                            "పరిచయం (Introduction) — Hook sentence, background context, clear thesis statement",
                            "ముఖ్యాంశాలు (Main Body) — 3–4 paragraphs; each paragraph = one clear idea",
                            "ఉపసంహారం (Conclusion) — Summary, personal view, way forward / future outlook",
                            "Ideal length: 600–800 words for APPSC examination essays",
                            "Use Telugu idiomatic expressions (నుడికారాలు) to enrich language",
                            "Incorporate Telugu proverbs (సామెతలు) where contextually appropriate",
                            "Quote relevant Telugu poets or literature to add scholarly depth",
                        ],
                    },
                    "essay_topics": {
                        "title": "Common APPSC Essay Topics",
                        "meta": "Essay • Topic Bank",
                        "points": [
                            "తెలుగు భాష ప్రాముఖ్యత — Importance and glory of the Telugu language",
                            "స్త్రీ విద్య — Women's education and empowerment in modern India",
                            "పర్యావరణ సంరక్షణ — Environmental conservation and climate change",
                            "ప్రజాస్వామ్యం — Democracy: strengths, challenges, and responsibilities",
                            "నీటి సమస్య — Water scarcity: causes, impact, and management",
                            "సాంకేతిక పరిజ్ఞానం — Technology and its impact on society",
                            "గ్రామీణాభివృద్ధి — Rural development and upliftment",
                            "మాదక ద్రవ్యాల దుష్ప్రభావం — Ill effects of drug abuse on youth",
                            "జాతీయ సమైక్యత — National integration and unity in diversity",
                            "యువత పాత్ర — Role of youth in nation building",
                        ],
                    },
                    "essay_language": {
                        "title": "Useful Phrases for Essays",
                        "meta": "Essay • Language Bank",
                        "points": [
                            "మొదట / అన్నింటికంటే ముందుగా — Firstly / To begin with",
                            "అదే విధంగా / అలాగే — Similarly / In the same way",
                            "అయినప్పటికీ / అయినా — However / Nevertheless",
                            "కాబట్టి / అందుకే — Therefore / Hence",
                            "పైన చెప్పిన విషయాలను బట్టి — Based on the above points",
                            "సమాజంలో మార్పు తీసుకురావాలంటే — To bring change in society",
                            "ప్రభుత్వం తగిన చర్యలు తీసుకోవాలి — The government must take appropriate steps",
                            "ముగింపుగా చెప్పాలంటే — In conclusion / To sum up",
                        ],
                    },
                },
            },
        },
    },
}


async def telugu(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "telugu.html", {
        "structure_json": json.dumps(TELUGU_STRUCTURE),
        "current_user": user,
        "user_id": user["id"] if user else None,
    })


# ---------------------------------------------------------------------------
# Current Affairs
# ---------------------------------------------------------------------------

def _ca_days_for_month(year: int, month: int) -> list[int]:
    """Return sorted list of day numbers that have a CA markdown file."""
    days: list[int] = []
    if CA_DIR.exists():
        for f in CA_DIR.glob(f"{year}-{month:02d}-*.md"):
            try:
                days.append(int(f.stem.split("-")[2]))
            except (IndexError, ValueError):
                pass
    return sorted(days)


def _ca_weeks_for_month(year: int, month: int):
    """Return (days, weekly_ranges) where each range covers file_day to next_file_day-1 (max 7 days)."""
    days = _ca_days_for_month(year, month)
    if not days:
        return [], []
    last_day = (date(year, month % 12 + 1, 1) - timedelta(days=1)).day if month < 12 else 31
    weekly_ranges = []
    for i, d in enumerate(days):
        end = min(d + 6, last_day)
        if i + 1 < len(days):
            end = min(end, days[i + 1] - 1)
        weekly_ranges.append({"file_day": d, "start": d, "end": end})
    return days, weekly_ranges


async def current_affairs(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "current_affairs.html", {
        "current_user": user,
    })


async def api_ca_content(request: Request):
    """Return raw markdown for a given date, or 404 if not found."""
    date = request.path_params["date"]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return PlainTextResponse("Invalid date format.", status_code=400)
    ca_file = CA_DIR / f"{date}.md"
    if not ca_file.exists():
        return PlainTextResponse("", status_code=404)
    return PlainTextResponse(
        ca_file.read_text(encoding="utf-8"),
        headers={"Cache-Control": "public, max-age=900"},  # 15 min — CA files are stable once published
    )


async def api_ca_month(request: Request):
    """Return CA days and weekly ranges so the calendar can highlight full weeks."""
    try:
        year  = int(request.path_params["year"])
        month = int(request.path_params["month"])
    except ValueError:
        return JSONResponse({"error": "Invalid year/month"}, status_code=400)
    days, weekly_ranges = _ca_weeks_for_month(year, month)
    return JSONResponse({"days": days, "weekly_ranges": weekly_ranges})


async def api_ca_mark_read(request: Request):
    """POST {"date": "YYYY-MM-DD"} — mark a CA date as read for the current user."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    ca_date = str(body.get("date", "")).strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", ca_date):
        return JSONResponse({"error": "Invalid date"}, status_code=400)
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT OR IGNORE INTO ca_reads (user_id, ca_date) VALUES (?, ?)",
        (user["id"], ca_date)
    )
    con.commit()
    con.close()
    return JSONResponse({"ok": True})


async def api_ca_read_status(request: Request):
    """GET read dates for a given year/month for the current user."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"read_dates": []})
    try:
        year  = int(request.path_params["year"])
        month = int(request.path_params["month"])
    except ValueError:
        return JSONResponse({"error": "Invalid year/month"}, status_code=400)
    prefix = f"{year}-{str(month).zfill(2)}-"
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT ca_date FROM ca_reads WHERE user_id=? AND ca_date LIKE ?",
        (user["id"], prefix + "%")
    ).fetchall()
    con.close()
    return JSONResponse({"read_dates": [r[0] for r in rows]})


async def api_ca_stats(request: Request):
    """GET total CA read count and current streak for the current user."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"total": 0, "streak": 0})
    con = sqlite3.connect(DB_PATH)
    total = con.execute(
        "SELECT COUNT(*) FROM ca_reads WHERE user_id=?", (user["id"],)
    ).fetchone()[0]
    # Compute streak: consecutive weeks read going back from most recent
    rows = con.execute(
        "SELECT ca_date FROM ca_reads WHERE user_id=? ORDER BY ca_date DESC",
        (user["id"],)
    ).fetchall()
    con.close()
    streak = 0
    if rows:
        from datetime import timedelta
        dates = sorted([r[0] for r in rows], reverse=True)
        # Find all CA file dates available on disk
        ca_dates_on_disk = sorted(
            [f.stem for f in CA_DIR.glob("*.md") if re.match(r"\d{4}-\d{2}-\d{2}", f.stem)],
            reverse=True
        )
        read_set = set(dates)
        # Walk ca_dates_on_disk from latest; streak breaks when a file is not read
        for ca_d in ca_dates_on_disk:
            if ca_d in read_set:
                streak += 1
            else:
                break
    return JSONResponse({"total": total, "streak": streak})


async def ca_digest_page(request: Request):
    """Monthly digest page — all CA entries for a month in one scrollable view."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    try:
        year  = int(request.path_params["year"])
        month = int(request.path_params["month"])
    except ValueError:
        return PlainTextResponse("Invalid year/month", status_code=400)

    prefix = f"{year}-{str(month).zfill(2)}-"
    entries = []
    for f in sorted(CA_DIR.glob(f"{prefix}*.md")):
        text = f.read_text(encoding="utf-8")
        # Strip QUIZ blocks
        text = re.sub(r'<!--\s*QUIZ[\s\S]*?-->', '', text).strip()
        entries.append({"date": f.stem, "content": text})

    month_name = ["", "January","February","March","April","May","June",
                  "July","August","September","October","November","December"][month]
    return templates.TemplateResponse(request, "ca_digest.html", {
        "entries": entries,
        "year": year,
        "month": month,
        "month_name": month_name,
        "current_user": user,
    })


async def api_ca_digest(request: Request):
    """API: Return all CA entries for a given month."""
    try:
        year  = int(request.path_params["year"])
        month = int(request.path_params["month"])
    except ValueError:
        return JSONResponse({"error": "Invalid year/month"}, status_code=400)
    prefix = f"{year}-{str(month).zfill(2)}-"
    entries = []
    for f in sorted(CA_DIR.glob(f"{prefix}*.md")):
        text = f.read_text(encoding="utf-8")
        text = re.sub(r'<!--\s*QUIZ[\s\S]*?-->', '', text).strip()
        entries.append({"date": f.stem, "content": text})
    return JSONResponse({"entries": entries})


async def api_ca_heatmap(request: Request):
    """GET 90-day heatmap: available CA dates + user read dates."""
    from datetime import timedelta
    user = get_current_user(request)
    today_d = date.today()
    start_d = today_d - timedelta(days=89)  # 90 days inclusive

    # All CA file dates in range
    all_ca = sorted([
        f.stem for f in CA_DIR.glob("*.md")
        if re.match(r"\d{4}-\d{2}-\d{2}", f.stem)
        and start_d.isoformat() <= f.stem <= today_d.isoformat()
    ])

    read_dates: list = []
    if user:
        con = sqlite3.connect(DB_PATH)
        rows = con.execute(
            "SELECT ca_date FROM ca_reads WHERE user_id=? AND ca_date>=? AND ca_date<=?",
            (user["id"], start_d.isoformat(), today_d.isoformat())
        ).fetchall()
        con.close()
        read_dates = [r[0] for r in rows]

    return JSONResponse({
        "available_dates": all_ca,
        "read_dates": read_dates,
        "start": start_d.isoformat(),
        "end": today_d.isoformat(),
    })


# ---------------------------------------------------------------------------
# Progress API — 1-4-7 revision tracker
# ---------------------------------------------------------------------------

def _progress_con():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


async def api_mark_studied(request: Request):
    """POST {topic_id, subject, topic_title, action} — upsert topic_progress or delete if action='unmark'."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    topic_id    = str(body.get("topic_id", "")).strip()
    subject     = str(body.get("subject", "")).strip()
    topic_title = str(body.get("topic_title", "")).strip()
    action      = str(body.get("action", "")).strip().lower()

    if not topic_id or not subject:
        return JSONResponse({"error": "topic_id and subject required"}, status_code=400)

    con = _progress_con()
    
    if action == "unmark":
        targets = [topic_id]
        twins = SHARED_TOPICS.get(topic_id, [])
        for twin in twins:
            # Handle both string IDs and dictionary records
            tid = twin["id"] if isinstance(twin, dict) else twin
            targets.append(tid)
            
        for tid in targets:
            con.execute("DELETE FROM topic_progress WHERE user_id=? AND topic_id=?", (user["id"], tid))
            con.execute("DELETE FROM revision_log WHERE user_id=? AND topic_id=?", (user["id"], tid))
        con.commit()
        con.close()
        return JSONResponse({"status": "unmarked", "topic_id": topic_id})

    today_str = date.today().isoformat()

    def _upsert(uid, tid, subj, title):
        existing = con.execute(
            "SELECT id, first_studied, study_count FROM topic_progress WHERE user_id=? AND topic_id=?",
            (uid, tid)
        ).fetchone()
        if existing:
            con.execute(
                "UPDATE topic_progress SET last_studied=?, study_count=study_count+1 WHERE user_id=? AND topic_id=?",
                (today_str, uid, tid)
            )
            return dict(existing)["first_studied"]
        else:
            con.execute(
                "INSERT INTO topic_progress (user_id, topic_id, subject, topic_title, first_studied, last_studied, study_count) VALUES (?,?,?,?,?,?,1)",
                (uid, tid, subj, title, today_str, today_str)
            )
            return today_str

    first_studied = _upsert(user["id"], topic_id, subject, topic_title)

    # Twins for marking
    twins = SHARED_TOPICS.get(topic_id, [])
    for twin in twins:
        twin_id = twin["id"] if isinstance(twin, dict) else twin
        twin_label = twin.get("label", topic_title) if isinstance(twin, dict) else topic_title
        twin_subj = "g2" if twin_id.startswith(("scr-", "p1-", "p2-")) else "g1"
        _upsert(user["id"], twin_id, twin_subj, twin_label)

    con.commit()
    con.close()
    return JSONResponse({"status": "success", "topic_id": topic_id})


async def api_mark_revised(request: Request):
    """POST {topic_id, revision_number} — record a completed revision."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    topic_id        = str(body.get("topic_id", "")).strip()
    revision_number = int(body.get("revision_number", 0))
    if not topic_id or revision_number not in (1, 2, 3):
        return JSONResponse({"error": "topic_id and revision_number (1/2/3) required"}, status_code=400)

    con = _progress_con()
    try:
        con.execute(
            "INSERT OR IGNORE INTO revision_log (user_id, topic_id, revision_number) VALUES (?,?,?)",
            (user["id"], topic_id, revision_number)
        )
        con.commit()
    finally:
        con.close()
    return JSONResponse({"ok": True})


async def api_due_today(request: Request):
    """GET — return topics where the next scheduled revision is due today or overdue."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    today = date.today()
    con = _progress_con()

    rows = con.execute(
        "SELECT topic_id, subject, topic_title, first_studied FROM topic_progress WHERE user_id=?",
        (user["id"],)
    ).fetchall()

    done_rows = con.execute(
        "SELECT topic_id, revision_number FROM revision_log WHERE user_id=?",
        (user["id"],)
    ).fetchall()
    con.close()

    done_set = {(r["topic_id"], r["revision_number"]) for r in done_rows}
    due_offsets = {1: 1, 2: 4, 3: 7}  # revision_number -> days after first_studied

    results = []
    for row in rows:
        try:
            first = date.fromisoformat(row["first_studied"])
        except Exception:
            continue
        for rev_num, offset in due_offsets.items():
            if (row["topic_id"], rev_num) in done_set:
                continue
            due_date = first + timedelta(days=offset)
            if due_date <= today:
                days_overdue = (today - due_date).days
                results.append({
                    "topic_id":       row["topic_id"],
                    "subject":        row["subject"],
                    "topic_title":    row["topic_title"],
                    "revision_number": rev_num,
                    "due_date":       due_date.isoformat(),
                    "days_overdue":   days_overdue,
                })
            break  # only show the earliest pending revision per topic

    results.sort(key=lambda x: (x["days_overdue"], x["topic_id"]), reverse=True)
    return JSONResponse({"due": results})


async def api_batch_status(request: Request):
    """GET ?ids=id1,id2,... — return study status for each topic_id."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({})

    raw = request.query_params.get("ids", "")
    ids = [i.strip() for i in raw.split(",") if i.strip()]
    if not ids:
        return JSONResponse({})

    con = _progress_con()
    placeholders = ",".join("?" * len(ids))
    prog_rows = con.execute(
        f"SELECT topic_id, first_studied, study_count FROM topic_progress WHERE user_id=? AND topic_id IN ({placeholders})",
        [user["id"]] + ids
    ).fetchall()
    rev_rows = con.execute(
        f"SELECT topic_id, revision_number FROM revision_log WHERE user_id=? AND topic_id IN ({placeholders})",
        [user["id"]] + ids
    ).fetchall()
    con.close()

    status = {}
    for r in prog_rows:
        status[r["topic_id"]] = {"first_studied": r["first_studied"], "study_count": r["study_count"], "revisions_done": []}
    for r in rev_rows:
        if r["topic_id"] in status:
            status[r["topic_id"]]["revisions_done"].append(r["revision_number"])

    return JSONResponse(status)


async def api_progress_summary(request: Request):
    """GET — overall progress stats for the logged-in user."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"total_studied": 0, "mastered": 0, "streak_days": 0, "by_subject": {}})

    con = _progress_con()
    prog_rows = con.execute(
        "SELECT topic_id, subject, first_studied, last_studied FROM topic_progress WHERE user_id=?",
        (user["id"],)
    ).fetchall()
    rev_rows = con.execute(
        "SELECT topic_id FROM revision_log WHERE user_id=? GROUP BY topic_id HAVING COUNT(DISTINCT revision_number)=3",
        (user["id"],)
    ).fetchall()
    con.close()

    mastered_set = {r["topic_id"] for r in rev_rows}
    by_subject = {}
    study_dates = set()
    for r in prog_rows:
        subj = r["subject"]
        by_subject[subj] = by_subject.get(subj, 0) + 1
        if r["last_studied"]:
            study_dates.add(r["last_studied"])

    # Streak: consecutive days up to and including today
    today = date.today()
    streak = 0
    check = today
    while check.isoformat() in study_dates:
        streak += 1
        check -= timedelta(days=1)

    return JSONResponse({
        "total_studied": len(prog_rows),
        "mastered":      len(mastered_set),
        "streak_days":   streak,
        "by_subject":    by_subject,
    })


async def api_progress_grid(request: Request):
    """GET — Returns a flattened list of all syllabus topics and their completion status."""
    user = get_current_user(request)
    if not user:
        return JSONResponse([])

    # 1. Gather all topic IDs from Group 2 and Group 1
    topics = []
    
    # helper to traverse syllabus structures
    def extract_topics(structure, exam_label):
        for area_key, area in structure.items():
            area_label = area.get("label", area_key.title())
            for section in area.get("sections", []):
                section_title = section.get("title", "Other")
                for topic in section.get("topics", []):
                    topics.append({
                        "id": topic["id"],
                        "title": topic["title"],
                        "exam": exam_label,
                        "area": area_label,
                        "section": section_title,
                        "minutes": 0 # Default, will be updated below
                    })

    extract_topics(G2_STRUCTURE, "Group II")
    extract_topics(G1_STRUCTURE, "Group I")

    # --- Aptitude ---
    for section in APT_STRUCTURE.get("sections", []):
        section_title = section.get("title", "Aptitude")
        for topic in section.get("topics", []):
            topics.append({
                "id": topic["id"],
                "title": topic["title"],
                "exam": "Aptitude",
                "area": section_title,
                "section": section_title
            })

    # --- Telugu ---
    for cat_key, cat in TELUGU_STRUCTURE.items():
        cat_label = cat.get("label", cat_key.title())
        for sec_key, sec in cat.get("sections", {}).items():
            sec_label = sec.get("label", sec_key.title())
            for topic_key, topic in sec.get("topics", {}).items():
                topics.append({
                    "id": f"telugu:{cat_key}:{sec_key}:{topic_key}",
                    "title": topic["title"],
                    "exam": "Telugu",
                    "area": cat_label,
                    "section": sec_label
                })

    # 2. Get User Progress
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        prog_rows = con.execute(
            "SELECT topic_id, study_count, minutes_spent FROM topic_progress WHERE user_id=?",
            (user["id"],)
        ).fetchall()

    done_data = {r["topic_id"]: {"count": r["study_count"], "minutes": r["minutes_spent"]} for r in prog_rows}

    # 3. Merge
    results = []
    for t in topics:
        stats = done_data.get(t["id"], {"count": 0, "minutes": 0})
        results.append({
            "id": t["id"],
            "title": t["title"],
            "exam": t["exam"],
            "area": t["area"],
            "section": t["section"],
            "completed": t["id"] in done_data,
            "minutes": stats["minutes"]
        })

    return JSONResponse(results)



async def api_get_pomodoro_settings(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Auth required"}, status_code=401)
    
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT work_min, break_min FROM user_pomodoro_settings WHERE user_id = ?", (user["id"],)).fetchone()
        if row:
            return JSONResponse(dict(row))
        return JSONResponse({"work_min": 25, "break_min": 5})

async def api_save_pomodoro_settings(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Auth required"}, status_code=401)
    
    try:
        data = await request.json()
        work = int(data.get("work_min", 25))
        break_m = int(data.get("break_min", 5))
        
        with sqlite3.connect(DB_PATH) as con:
            con.execute("""
                INSERT INTO user_pomodoro_settings (user_id, work_min, break_min, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    work_min = EXCLUDED.work_min,
                    break_min = EXCLUDED.break_min,
                    updated_at = CURRENT_TIMESTAMP
            """, (user["id"], work, break_m))
            con.commit()
        return JSONResponse({"status": "ok"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

async def api_study_log(request: Request):
    """POST — Logs study minutes for a specific topic."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Auth required"}, status_code=401)
    
    try:
        data = await request.json()
        topic_id = data.get("topic_id")
        minutes  = int(data.get("minutes", 1))
        
        if not topic_id:
            return JSONResponse({"error": "topic_id required"}, status_code=400)
            
        with sqlite3.connect(DB_PATH) as con:
            con.execute("""
                INSERT INTO topic_progress (user_id, topic_id, minutes_spent, first_studied, last_studied, subject, topic_title)
                VALUES (?, ?, ?, CURRENT_DATE, CURRENT_DATE, 'Active', 'Active')
                ON CONFLICT(user_id, topic_id) DO UPDATE SET
                    minutes_spent = minutes_spent + EXCLUDED.minutes_spent,
                    last_studied = CURRENT_DATE
            """, (user["id"], topic_id, minutes))
            con.commit()
            
        return JSONResponse({"status": "ok"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "dashboard.html", {
        "current_user": user,
        "today": date.today().isoformat(),
    })


# ---------------------------------------------------------------------------
# Admin Panel
# ---------------------------------------------------------------------------

async def admin_page(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "admin.html", {
        "current_user": user
    })

async def api_admin_users(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
        
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT id, username, display_name, email, role, created_at FROM users ORDER BY created_at DESC").fetchall()
    con.close()
    return JSONResponse([dict(r) for r in rows])

async def api_admin_delete_user(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
        
    uid = request.path_params["id"]
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM users WHERE id = ?", (uid,))
    con.commit()
    con.close()
    return JSONResponse({"ok": True})

async def api_admin_role_user(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
        
    uid = request.path_params["id"]
    body = await request.json()
    new_role = str(body.get("role", "student")).strip()
    
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, uid))
    con.commit()
    con.close()
    return JSONResponse({"ok": True})

async def api_admin_ca_list(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
        
    files = []
    if CA_DIR.exists():
        for f in CA_DIR.glob("*.md"):
            files.append(f.name)
    files.sort(reverse=True)
    return JSONResponse({"files": files})

async def api_admin_ca_save(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
        
    body = await request.json()
    date_str = str(body.get("date", "")).strip()
    content = str(body.get("content", ""))
    
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return JSONResponse({"error": "Invalid date format"}, status_code=400)
        
    CA_DIR.mkdir(parents=True, exist_ok=True)
    ca_file = CA_DIR / f"{date_str}.md"
    ca_file.write_text(content, encoding="utf-8")
    return JSONResponse({"ok": True})

async def api_admin_ca_delete(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
        
    date_str = request.path_params["date"]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return JSONResponse({"error": "Invalid date format"}, status_code=400)
        
    ca_file = CA_DIR / f"{date_str}.md"
    if ca_file.exists():
        ca_file.unlink()
    return JSONResponse({"ok": True})


# ── Admin Topic Content API ───────────────────────────────────────────────────

async def api_admin_list_topics(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    
    topics = []
    # Collect from G1, G2, Aptitude
    for s in G1_STRUCTURE.values():
        for sec in s["sections"]:
            for t in sec["topics"]:
                topics.append({"id": t["id"], "title": f"G1: {t['title']}"})
    for s in G2_STRUCTURE.values():
        for sec in s["sections"]:
            for t in sec["topics"]:
                topics.append({"id": t["id"], "title": f"G2: {t['title']}"})
    for sec in APT_STRUCTURE["sections"]:
        for t in sec["topics"]:
            topics.append({"id": t["id"], "title": f"APT: {t['title']}"})
    
    return JSONResponse({"topics": sorted(topics, key=lambda x: x["title"])})


async def api_admin_save_topic(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    
    body = await request.json()
    topic_id = body.get("topic_id")
    content = body.get("content")
    if not topic_id or content is None:
        return JSONResponse({"error": "Missing data"}, status_code=400)
    
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    path = NOTES_DIR / f"{topic_id}.md"
    path.write_text(content, encoding="utf-8")
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Auth route handlers
# ---------------------------------------------------------------------------

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_\-]{3,20}$')


async def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=302)
    registered = request.query_params.get("registered") == "1"
    
    err_code = request.query_params.get("error")
    error_msg = None
    if err_code == "oauth_not_configured":
        error_msg = "Google login is currently disabled. Please use username/password."
    elif err_code == "oauth_failed":
        error_msg = "Google login failed. Please try again."
    elif err_code == "invalid_state":
        error_msg = "Invalid session state. Please try again."
    elif err_code == "no_email":
        error_msg = "Google account did not provide an email address."
        
    return templates.TemplateResponse(request, "auth.html", {
        "current_user": None,
        "error": error_msg,
        "registered": registered,
        "mode": "login",
    })


async def login_post(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=302)
    form = await request.form()
    raw_username = str(form.get("username", "")).strip().lower()
    password     = str(form.get("password", ""))
    # Strip @groupsguru.in if user typed the full address
    username = raw_username.replace("@groupsguru.in", "")

    user = db_get_user_by_username(username)
    if user and user["is_active"] and verify_password(password, user["password_hash"]):
        request.session["user_id"]  = user["id"]
        request.session["username"] = user["username"]
        request.session["role"]     = user["role"]
        return RedirectResponse("/dashboard", status_code=302)

    return templates.TemplateResponse(request, "auth.html", {
        "current_user": None,
        "error": "Invalid username or password.",
        "registered": False,
        "mode": "login",
    }, status_code=200)


async def register_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "auth.html", {
        "current_user": None,
        "error": None,
        "mode": "register",
    })


async def register_post(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=302)
    form = await request.form()
    username     = str(form.get("username", "")).strip().lower()
    display_name = str(form.get("display_name", "")).strip()
    email        = str(form.get("email", "")).strip()
    password     = str(form.get("password", ""))
    confirm_pwd  = str(form.get("confirm_password", ""))

    def fail(msg):
        return templates.TemplateResponse(request, "auth.html", {
            "current_user": None,
            "error": msg,
            "mode": "register",
            "vals": {"username": username, "display_name": display_name, "email": email},
        }, status_code=200)

    if not _USERNAME_RE.match(username):
        return fail("Username must be 3–20 characters: letters, numbers, _ or - only.")
    if not display_name:
        return fail("Display name is required.")
    if len(password) < 8:
        return fail("Password must be at least 8 characters.")
    if password != confirm_pwd:
        return fail("Passwords do not match.")
    if db_username_taken(username):
        return fail(f"Username '{username}' is already taken. Please choose another.")

    db_create_user(username, display_name, email, password)
    return RedirectResponse("/login?registered=1", status_code=302)


async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html", {
        "current_user": get_current_user(request),
        "error": None,
        "success": None,
    })


async def forgot_password_post(request: Request):
    form = await request.form()
    email_addr = str(form.get("email", "")).strip()
    
    user = db_get_user_by_email(email_addr)
    if user and EMAIL_USER and EMAIL_PASS:
        token = secrets.token_urlsafe(32)
        expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        
        con = sqlite3.connect(DB_PATH)
        con.execute("INSERT INTO password_resets (token, user_id, expires_at) VALUES (?, ?, ?)", (token, user['id'], expires))
        con.commit()
        con.close()
        
        reset_url = str(request.base_url).rstrip("/") + "/reset-password?token=" + token
        
        msg = EmailMessage()
        msg.set_content(f"Hi {user['display_name']},\n\nClick the link below to reset your password:\n\n{reset_url}\n\nThis link expires in 1 hour.")
        msg['Subject'] = 'GroupsGuru Password Reset'
        msg['From'] = EMAIL_USER
        msg['To'] = email_addr
        
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(EMAIL_USER, EMAIL_PASS)
                smtp.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")
            
    # Always return success to prevent email enumeration
    return templates.TemplateResponse(request, "forgot_password.html", {
        "current_user": get_current_user(request),
        "error": None,
        "success": "If an account exists with that email, a password reset link has been sent.",
    })


async def reset_password_page(request: Request):
    token = request.query_params.get("token")
    return templates.TemplateResponse(request, "reset_password.html", {
        "current_user": None,
        "error": None,
        "token": token,
    })


async def reset_password_post(request: Request):
    form = await request.form()
    token = str(form.get("token", ""))
    new_pwd = str(form.get("new_password", ""))
    confirm_pwd = str(form.get("confirm_password", ""))
    
    def fail(msg):
        return templates.TemplateResponse(request, "reset_password.html", {
            "current_user": None,
            "error": msg,
            "token": token,
        })
        
    if new_pwd != confirm_pwd:
        return fail("Passwords do not match.")
    if len(new_pwd) < 8:
        return fail("Password must be at least 8 characters.")
        
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM password_resets WHERE token = ?", (token,)).fetchone()
    
    if not row or datetime.fromisoformat(row['expires_at']) < datetime.utcnow():
        con.close()
        return fail("Invalid or expired reset link.")
        
    con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_pwd), row['user_id']))
    con.execute("DELETE FROM password_resets WHERE token = ?", (token,))
    con.commit()
    con.close()
    
    return RedirectResponse("/login?reset=1", status_code=302)


async def login_google(request: Request):
    if not GOOGLE_CLIENT_ID:
        return RedirectResponse("/login?error=oauth_not_configured", status_code=302)
    
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    redirect_uri = str(request.base_url).rstrip("/") + "/auth/google/callback"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


async def auth_google_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    saved_state = request.session.pop("oauth_state", None)

    if not code or not state or state != saved_state:
        return RedirectResponse("/login?error=invalid_state", status_code=302)
        
    redirect_uri = str(request.base_url).rstrip("/") + "/auth/google/callback"
    
    async with httpx.AsyncClient() as client:
        token_resp = await client.post("https://oauth2.googleapis.com/token", data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        })
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            return RedirectResponse("/login?error=oauth_failed", status_code=302)
            
        user_resp = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={
            "Authorization": f"Bearer {access_token}"
        })
        user_info = user_resp.json()
        
    email = user_info.get("email")
    if not email:
        return RedirectResponse("/login?error=no_email", status_code=302)
        
    # Check if user exists by email
    user = db_get_user_by_email(email)
    
    # If not, auto-create account based on google email
    if not user:
        username_base = email.split("@")[0].lower()
        username_base = re.sub(r'[^a-z0-9_-]', '', username_base)
        username = username_base
        
        con = sqlite3.connect(DB_PATH)
        # Ensure unique username
        suffix = 1
        while con.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            username = f"{username_base}{suffix}"
            suffix += 1
            
        display_name = user_info.get("name", username)
        
        con.execute(
            "INSERT INTO users (username, display_name, email, password_hash) VALUES (?,?,?,?)",
            (username, display_name, email, hash_password(secrets.token_urlsafe(20))), # random password
        )
        con.commit()
        con.close()
        
        user = db_get_user_by_email(email)
        
    request.session["user_id"]  = user["id"]
    request.session["username"] = user["username"]
    request.session["role"]     = user["role"]
    
    return RedirectResponse("/dashboard", status_code=302)


async def change_password_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "change_password.html", {
        "current_user": user,
        "error": None,
        "success": None,
    })


async def change_password_post(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    form        = await request.form()
    current_pwd = str(form.get("current_password", ""))
    new_pwd     = str(form.get("new_password", ""))
    confirm_pwd = str(form.get("confirm_password", ""))

    def fail(msg):
        return templates.TemplateResponse(request, "change_password.html", {
            "current_user": user,
            "error": msg,
            "success": None,
        }, status_code=200)

    db_user = db_get_user_by_username(user["username"])
    if not db_user or not verify_password(current_pwd, db_user["password_hash"]):
        return fail("Current password is incorrect.")
    if len(new_pwd) < 8:
        return fail("New password must be at least 8 characters.")
    if new_pwd != confirm_pwd:
        return fail("New passwords do not match.")

    db_update_password(user["id"], new_pwd)
    return templates.TemplateResponse(request, "change_password.html", {
        "current_user": user,
        "error": None,
        "success": "Password changed successfully.",
    }, status_code=200)


# ---------------------------------------------------------------------------
# Global Search
# ---------------------------------------------------------------------------

async def api_search(request: Request):
    q = (request.query_params.get("q") or "").strip().lower()
    if len(q) < 2:
        return JSONResponse([])

    results = []  # list of {subject, stage, topic_title, topic_id, snippet, url}

    def match_points(points, query):
        """Return first matching point as a snippet, or None."""
        for p in points:
            if query in p.lower():
                return p
        return None

    # --- G1 ---
    for stage_key, stage in G1_STRUCTURE.items():
        for section in stage["sections"]:
            for topic in section["topics"]:
                title_match = q in topic["title"].lower()
                snippet = match_points(topic["points"], q)
                if title_match or snippet:
                    results.append({
                        "subject": "Group I",
                        "stage": stage["label"],
                        "topic_title": topic["title"],
                        "topic_id": topic["id"],
                        "snippet": snippet or topic["points"][0] if topic["points"] else "",
                        "url": "/group1",
                    })

    # --- G2 ---
    for stage_key, stage in G2_STRUCTURE.items():
        for section in stage["sections"]:
            for topic in section["topics"]:
                title_match = q in topic["title"].lower()
                snippet = match_points(topic["points"], q)
                if title_match or snippet:
                    results.append({
                        "subject": "Group II",
                        "stage": stage["label"],
                        "topic_title": topic["title"],
                        "topic_id": topic["id"],
                        "snippet": snippet or topic["points"][0] if topic["points"] else "",
                        "url": "/group2",
                    })

    # --- Aptitude ---
    for section in APT_STRUCTURE["sections"]:
        for topic in section["topics"]:
            title_match = q in topic["title"].lower()
            snippet = match_points(topic["points"], q)
            if title_match or snippet:
                results.append({
                    "subject": "Aptitude",
                    "stage": topic.get("exam", "General"),
                    "topic_title": topic["title"],
                    "topic_id": topic["id"],
                    "snippet": snippet or topic["points"][0] if topic["points"] else "",
                    "url": "/aptitude",
                })

    # --- Telugu ---
    for tab_key, tab_data in TELUGU_STRUCTURE.items():
        for sec_key, sec in tab_data["sections"].items():
            for topic_key, topic in sec["topics"].items():
                title_match = q in topic["title"].lower()
                snippet = match_points(topic["points"], q)
                if title_match or snippet:
                    results.append({
                        "subject": "Telugu",
                        "stage": sec["label"],
                        "topic_title": topic["title"],
                        "topic_id": f"telugu:{tab_key}:{sec_key}:{topic_key}",
                        "snippet": snippet or topic["points"][0] if topic["points"] else "",
                        "url": "/telugu",
                    })
    # --- Current Affairs (markdown files) ---
    if CA_DIR.exists():
        for md_file in sorted(CA_DIR.glob("*.md"), reverse=True):
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
            date_str = md_file.stem  # e.g. "2026-04-14"
            lines = content.split("\n")
            heading = ""
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("## "):
                    heading = stripped[3:].strip()
                elif q in stripped.lower() and stripped and not stripped.startswith("#"):
                    # Clean up the bullet text for display
                    clean = stripped.lstrip("-*• ").strip()
                    results.append({
                        "subject": "Current Affairs",
                        "stage": heading or date_str,
                        "topic_title": date_str,
                        "topic_id": f"ca:{date_str}",
                        "snippet": clean,
                        "url": "/current-affairs",
                    })
            # Stop after scanning last 30 CA files to keep it fast
            if len([f for f in CA_DIR.glob("*.md")]) > 30:
                break

    return JSONResponse(results[:50])  # cap at 50


# ── Content Notes API ────────────────────────────────────────────────────────
NOTES_DIR = FILES_DIR / "content" / "topics"

async def api_get_content(request: Request):
    topic_id = request.path_params["topic_id"]
    if not re.match(r'^[a-z0-9-]+$', topic_id):
        return JSONResponse({"available": False})

    cache_headers = {"Cache-Control": "public, max-age=1800"}  # 30 min — content rarely changes

    # Direct file check
    direct = NOTES_DIR / f"{topic_id}.md"
    if direct.exists():
        return JSONResponse({"available": True, "content": direct.read_text("utf-8")}, headers=cache_headers)

    # Twin fallback via SHARED_TOPICS
    for twin in SHARED_TOPICS.get(topic_id, []):
        twin_file = NOTES_DIR / f"{twin['id']}.md"
        if twin_file.exists():
            return JSONResponse({
                "available": True,
                "content": twin_file.read_text("utf-8"),
                "source": twin["label"],
            }, headers=cache_headers)

    return JSONResponse({"available": False, "content": None})


# ── Highlights API ────────────────────────────────────────────────────────────

async def api_get_highlights(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    topic_id = request.path_params["topic_id"]
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT highlights_json FROM topic_highlights WHERE user_id=? AND topic_id=?",
        (user["id"], topic_id)
    ).fetchone()
    con.close()
    return JSONResponse({"highlights": json.loads(row[0]) if row else []})


async def api_save_highlights(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    topic_id = request.path_params["topic_id"]
    body = await request.json()
    highlights = body.get("highlights", [])
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO topic_highlights (user_id, topic_id, highlights_json, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, topic_id) DO UPDATE SET
            highlights_json=excluded.highlights_json,
            updated_at=CURRENT_TIMESTAMP
    """, (user["id"], topic_id, json.dumps(highlights)))
    con.commit()
    con.close()
    return JSONResponse({"ok": True})


# ── Personal Notes API ────────────────────────────────────────────────────────

async def api_get_user_notes(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    topic_id = request.path_params["topic_id"]
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT content FROM topic_user_notes WHERE user_id=? AND topic_id=?",
        (user["id"], topic_id)
    ).fetchone()
    con.close()
    return JSONResponse({"content": row[0] if row else ""})


async def api_save_user_notes(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    topic_id = request.path_params["topic_id"]
    body = await request.json()
    content = body.get("content", "")
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO topic_user_notes (user_id, topic_id, content, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, topic_id) DO UPDATE SET
            content=excluded.content,
            updated_at=CURRENT_TIMESTAMP
    """, (user["id"], topic_id, content))
    con.commit()
    con.close()
    return JSONResponse({"ok": True})


# ── Flashcards API ────────────────────────────────────────────────────────────

async def api_get_flashcards(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    topic_id = request.path_params["topic_id"]
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT id, front, back, created_at FROM flashcards WHERE user_id=? AND topic_id=? ORDER BY id",
        (user["id"], topic_id)
    ).fetchall()
    con.close()
    return JSONResponse({"cards": [{"id": r[0], "front": r[1], "back": r[2], "created_at": r[3]} for r in rows]})


async def api_create_flashcard(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    topic_id = request.path_params["topic_id"]
    body = await request.json()
    front = (body.get("front") or "").strip()
    back = (body.get("back") or "").strip()
    if not front:
        return JSONResponse({"error": "front is required"}, status_code=400)
    con = sqlite3.connect(DB_PATH)
    cur = con.execute(
        "INSERT INTO flashcards (user_id, topic_id, front, back) VALUES (?, ?, ?, ?)",
        (user["id"], topic_id, front, back)
    )
    card_id = cur.lastrowid
    con.commit()
    con.close()
    return JSONResponse({"ok": True, "id": card_id})


async def api_update_flashcard(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    card_id = int(request.path_params["id"])
    body = await request.json()
    back = (body.get("back") or "")
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "UPDATE flashcards SET back=? WHERE id=? AND user_id=?",
        (back, card_id, user["id"])
    )
    con.commit()
    con.close()
    return JSONResponse({"ok": True})


async def api_delete_flashcard(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    card_id = int(request.path_params["id"])
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM flashcards WHERE id=? AND user_id=?", (card_id, user["id"]))
    con.commit()
    con.close()
    return JSONResponse({"ok": True})


# ── Paragraph Pins API ────────────────────────────────────────────────────────

async def api_get_pins(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    topic_id = request.path_params["topic_id"]
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT para_index, para_text FROM paragraph_pins WHERE user_id=? AND topic_id=? ORDER BY para_index",
        (user["id"], topic_id)
    ).fetchall()
    con.close()
    return JSONResponse({"pins": [{"para_index": r[0], "para_text": r[1]} for r in rows]})


async def api_toggle_pin(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    topic_id = request.path_params["topic_id"]
    body = await request.json()
    para_index = int(body.get("para_index", -1))
    para_text = (body.get("para_text") or "").strip()
    con = sqlite3.connect(DB_PATH)
    existing = con.execute(
        "SELECT id FROM paragraph_pins WHERE user_id=? AND topic_id=? AND para_index=?",
        (user["id"], topic_id, para_index)
    ).fetchone()
    if existing:
        con.execute("DELETE FROM paragraph_pins WHERE user_id=? AND topic_id=? AND para_index=?",
                    (user["id"], topic_id, para_index))
        action = "removed"
    else:
        con.execute(
            "INSERT INTO paragraph_pins (user_id, topic_id, para_index, para_text) VALUES (?, ?, ?, ?)",
            (user["id"], topic_id, para_index, para_text)
        )
        action = "added"
    con.commit()
    con.close()
    return JSONResponse({"ok": True, "action": action})


async def api_all_pins(request: Request):
    """All pins for the current user across all topics — for Last-Day Revision page."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT topic_id, para_index, para_text, created_at FROM paragraph_pins WHERE user_id=? ORDER BY topic_id, para_index",
        (user["id"],)
    ).fetchall()
    con.close()
    # Group by topic_id
    grouped: dict = {}
    for topic_id, para_index, para_text, created_at in rows:
        grouped.setdefault(topic_id, []).append({"para_index": para_index, "para_text": para_text})
    return JSONResponse({"pins": grouped})


# ── Profile Page & Update API ─────────────────────────────────────────────────

async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT username, display_name, email, role, created_at FROM users WHERE id=?",
        (user["id"],)
    ).fetchone()
    topics_count   = con.execute("SELECT COUNT(*) FROM topic_progress WHERE user_id=?", (user["id"],)).fetchone()[0]
    revisions_count = con.execute("SELECT COUNT(*) FROM revision_log WHERE user_id=?", (user["id"],)).fetchone()[0]
    pins_count     = con.execute("SELECT COUNT(*) FROM paragraph_pins WHERE user_id=?", (user["id"],)).fetchone()[0]
    minutes_total  = con.execute("SELECT COALESCE(SUM(minutes_spent),0) FROM topic_progress WHERE user_id=?", (user["id"],)).fetchone()[0]
    con.close()
    return templates.TemplateResponse(request, "profile.html", {
        "current_user": user,
        "profile": {
            "username":     row["username"],
            "display_name": row["display_name"],
            "email":        row["email"] or "",
            "role":         row["role"],
            "joined":       (row["created_at"] or "")[:10],
        },
        "stats": {
            "topics":    topics_count,
            "revisions": revisions_count,
            "pins":      pins_count,
            "minutes":   minutes_total,
        },
    })


async def api_profile_update(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    display_name = str(body.get("display_name", "")).strip()
    email        = str(body.get("email", "")).strip()
    if not display_name:
        return JSONResponse({"error": "Display name cannot be empty"}, status_code=400)
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE users SET display_name=?, email=? WHERE id=?",
                (display_name, email or None, user["id"]))
    con.commit()
    con.close()
    return JSONResponse({"ok": True, "display_name": display_name})


# ── Leaderboard Page ──────────────────────────────────────────────────────────

async def leaderboard_page(request: Request):
    user = get_current_user(request)
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT
            u.id,
            u.display_name,
            u.username,
            COUNT(DISTINCT tp.topic_id)  AS topics,
            COUNT(DISTINCT rl.id)        AS revisions,
            COALESCE(SUM(tp.minutes_spent), 0) AS minutes
        FROM users u
        LEFT JOIN topic_progress tp ON tp.user_id = u.id
        LEFT JOIN revision_log   rl ON rl.user_id = u.id
        WHERE u.role = 'student' AND u.is_active = 1
        GROUP BY u.id
        ORDER BY (COUNT(DISTINCT tp.topic_id)*10 + COUNT(DISTINCT rl.id)*5) DESC
        LIMIT 50
    """).fetchall()
    con.close()
    leaders = []
    for i, r in enumerate(rows):
        leaders.append({
            "rank":         i + 1,
            "user_id":      r["id"],
            "display_name": r["display_name"],
            "username":     r["username"],
            "topics":       r["topics"],
            "revisions":    r["revisions"],
            "minutes":      r["minutes"],
            "score":        r["topics"] * 10 + r["revisions"] * 5,
            "is_me":        bool(user and r["id"] == user["id"]),
        })
    return templates.TemplateResponse(request, "leaderboard.html", {
        "current_user": user,
        "leaders":      leaders,
    })


# ── Topic Status API (for revision badge) ─────────────────────────────────────

async def api_topic_status(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    topic_id = request.path_params["topic_id"]
    
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        prog = con.execute(
            "SELECT first_studied, last_studied, study_count, minutes_spent FROM topic_progress WHERE user_id=? AND topic_id=?",
            (user["id"], topic_id)
        ).fetchone()
        revs = con.execute(
            "SELECT revision_number FROM revision_log WHERE user_id=? AND topic_id=? ORDER BY revision_number",
            (user["id"], topic_id)
        ).fetchall()
    
    if not prog:
        return JSONResponse({"studied": False, "minutes_spent": 0})
    
    # Calculate next revision
    from datetime import date as _date, timedelta
    first_studied = _date.fromisoformat(prog["first_studied"])
    last_studied = _date.fromisoformat(prog["last_studied"])
    today = _date.today()
    days_since = (today - last_studied).days
    revs_done = [r[0] for r in revs]
    
    # 1-4-7 schedule
    schedule = {1: first_studied + timedelta(days=1),
                2: first_studied + timedelta(days=4),
                3: first_studied + timedelta(days=7)}
    next_due = None
    next_rev_num = None
    days_until = None

    for rev_num in [1, 2, 3]:
        if rev_num not in revs_done:
            due_date = schedule[rev_num]
            next_due = due_date.isoformat()
            next_rev_num = rev_num
            days_until = (due_date - today).days
            break

    return JSONResponse({
        "studied": True,
        "first_studied": prog["first_studied"],
        "last_studied": prog["last_studied"],
        "days_since_studied": days_since,
        "study_count": prog["study_count"],
        "minutes_spent": prog["minutes_spent"] or 0,
        "revisions_done": revs_done,
        "next_revision_due": next_due,
        "next_revision_num": next_rev_num,
        "days_until_revision": days_until,
    })


# ── Last-Day Revision Page ────────────────────────────────────────────────────

async def last_day_revision(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "last_day_revision.html", {
        "current_user": user,
    })

# ── Dedicated Study Desk ──────────────────────────────────────────────────────

async def study_desk(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    slug = request.path_params["topic_id"]
    topic_id = SLUG_TO_ID.get(slug, slug)
    info = TOPIC_INDEX.get(topic_id, {})
    topic_title = info.get("title") or request.query_params.get("title") or topic_id
    # Redirect raw internal IDs to their clean slug URL
    if slug == topic_id and info.get("slug"):
        return RedirectResponse(f"/study-desk/{info['slug']}", status_code=301)
    return templates.TemplateResponse(request, "study_desk.html", {
        "current_user": user,
        "user_id": user["id"],
        "topic_id": topic_id,
        "topic_title": topic_title,
    })


# ── Practice (MCQ) Page ──────────────────────────────────────────────────────

async def practice_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    topic_id = request.path_params["topic_id"]
    
    # Try to find human title
    topic_title = topic_id
    for stage in G2_STRUCTURE.values():
        for section in stage["sections"]:
            for t in section["topics"]:
                if t["id"] == topic_id:
                    topic_title = t["title"]
                    break

    return templates.TemplateResponse(request, "practice.html", {
        "current_user": user,
        "user_id": user["id"],
        "topic_id": topic_id,
        "topic_title": topic_title,
    })


async def api_get_mcqs(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    topic_id = request.path_params["topic_id"]
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, question, option_a, option_b, option_c, option_d, correct_option, explanation FROM mcqs WHERE topic_id=? ORDER BY id",
        (topic_id,)
    ).fetchall()
    con.close()
    return JSONResponse({"mcqs": [dict(r) for r in rows]})


# ---------------------------------------------------------------------------
# Routing table
# ---------------------------------------------------------------------------

routes = [
    Route("/",                                    homepage),
    Route("/dashboard",                           dashboard),
    Route("/group1",                              group1),
    Route("/group2",                              group2),
    Route("/current-affairs",                    current_affairs),
    Route("/aptitude",                            aptitude),
    Route("/telugu",                              telugu),
    Route("/login",                               login_page,              methods=["GET"]),
    Route("/login",                               login_post,              methods=["POST"]),
    Route("/login/google",                        login_google,            methods=["GET"]),
    Route("/auth/google/callback",                auth_google_callback,    methods=["GET"]),
    Route("/register",                            register_page,           methods=["GET"]),
    Route("/register",                            register_post,           methods=["POST"]),
    Route("/logout",                              logout),
    Route("/forgot-password",                     forgot_password_page,    methods=["GET"]),
    Route("/forgot-password",                     forgot_password_post,    methods=["POST"]),
    Route("/reset-password",                      reset_password_page,     methods=["GET"]),
    Route("/reset-password",                      reset_password_post,     methods=["POST"]),
    Route("/change-password",                    change_password_page,    methods=["GET"]),
    Route("/change-password",                    change_password_post,    methods=["POST"]),
    Route("/api/ca/content/{date}",               api_ca_content),
    Route("/api/ca/month/{year}/{month}",         api_ca_month),
    Route("/api/ca/mark-read",                    api_ca_mark_read,        methods=["POST"]),
    Route("/api/ca/read-status/{year}/{month}",   api_ca_read_status),
    Route("/api/ca/stats",                        api_ca_stats),
    Route("/api/ca/heatmap",                      api_ca_heatmap),
    Route("/current-affairs/digest/{year}/{month}", ca_digest_page),
    Route("/api/ca/digest/{year}/{month}",        api_ca_digest),
    Route("/api/progress/mark-studied",           api_mark_studied,        methods=["POST"]),
    Route("/api/progress/mark-revised",           api_mark_revised,        methods=["POST"]),
    Route("/api/progress/due-today",              api_due_today),
    Route("/api/progress/batch-status",           api_batch_status),
    Route("/api/progress/summary",                api_progress_summary),
    Route("/api/progress/grid",                   api_progress_grid),
    Route("/api/study/log",                       api_study_log,           methods=["POST"]),
    Route("/api/pomodoro/settings",               api_get_pomodoro_settings,methods=["GET"]),
    Route("/api/pomodoro/settings",               api_save_pomodoro_settings,methods=["POST"]),
    Route("/admin",                               admin_page),
    Route("/api/admin/users",                     api_admin_users),
    Route("/api/admin/users/{id}",                api_admin_delete_user,   methods=["DELETE"]),
    Route("/api/admin/users/{id}/role",           api_admin_role_user,     methods=["POST"]),
    Route("/api/admin/ca",                        api_admin_ca_list),
    Route("/api/admin/ca",                        api_admin_ca_save,       methods=["POST"]),
    Route("/api/admin/ca/{date}",                 api_admin_ca_delete,     methods=["DELETE"]),
    Route("/api/admin/topics",                    api_admin_list_topics,   methods=["GET"]),
    Route("/api/admin/topics",                    api_admin_save_topic,    methods=["POST"]),
    Route("/api/search",                          api_search),
    Route("/api/content/{topic_id}",              api_get_content),
    Route("/api/highlights/{topic_id}",           api_get_highlights,       methods=["GET"]),
    Route("/api/highlights/{topic_id}",           api_save_highlights,      methods=["POST"]),
    Route("/api/user-notes/{topic_id}",           api_get_user_notes,       methods=["GET"]),
    Route("/api/user-notes/{topic_id}",           api_save_user_notes,      methods=["POST"]),
    Route("/api/flashcards/{topic_id}",           api_get_flashcards,       methods=["GET"]),
    Route("/api/flashcards/{topic_id}",           api_create_flashcard,     methods=["POST"]),
    Route("/api/flashcards/card/{id}",            api_update_flashcard,     methods=["PUT"]),
    Route("/api/flashcards/card/{id}",            api_delete_flashcard,     methods=["DELETE"]),
    Route("/api/pins/{topic_id}",                 api_get_pins,             methods=["GET"]),
    Route("/api/pins/{topic_id}",                 api_toggle_pin,           methods=["POST"]),
    Route("/api/pins",                            api_all_pins,             methods=["GET"]),
    Route("/api/progress/topic-status/{topic_id}", api_topic_status,        methods=["GET"]),
    Route("/api/mcqs/{topic_id}",                 api_get_mcqs,             methods=["GET"]),
    Route("/profile",                             profile_page),
    Route("/api/profile/update",                  api_profile_update,      methods=["POST"]),
    Route("/leaderboard",                         leaderboard_page),
    Route("/last-day-revision",                   last_day_revision),
    Route("/study-desk/{topic_id}",               study_desk),
    Route("/practice/{topic_id}",                 practice_page),
    Route("/robots.txt",                          lambda r: PlainTextResponse(open(STATIC_DIR / "robots.txt").read())),
    Route("/sitemap.xml",                         lambda r: PlainTextResponse(open(STATIC_DIR / "sitemap.xml").read(), media_type="application/xml")),
    Mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static"),
    Mount("/pdfs",   StaticFiles(directory=str(FILES_DIR)),  name="pdfs"),
]

app = Starlette(
    routes=routes,
    middleware=[Middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=False)],
)

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    if not os.environ.get("RENDER"):
        print("=" * 50)
        print("  GroupsGuru — APPSC 2026")
        print("  Open: http://localhost:8000")
        print("  Admin: admin@groupsguru.in")
        print("  Press Ctrl+C to stop")
        print("=" * 50)
    uvicorn.run(app, host=host, port=port)
