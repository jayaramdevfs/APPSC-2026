import json
import os
import re
from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
import uvicorn

BASE_DIR      = Path(__file__).parent
ROOT_DIR      = BASE_DIR.parent
FILES_DIR     = ROOT_DIR / "FILES"
CA_DIR        = FILES_DIR / "current-affairs"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR    = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---------------------------------------------------------------------------
# Group 2 — Official Syllabus Structure
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
# Group 1 — Official Syllabus Structure
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
    return templates.TemplateResponse(request, "index.html")


async def group1(request: Request):
    return templates.TemplateResponse(request, "group1.html", {
        "structure": G1_STRUCTURE,
        "structure_json": json.dumps(G1_STRUCTURE),
    })


async def group2(request: Request):
    return templates.TemplateResponse(request, "group2.html", {
        "structure": G2_STRUCTURE,
        "structure_json": json.dumps(G2_STRUCTURE),
    })






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


async def aptitude(request: Request):
    return templates.TemplateResponse(request, "aptitude.html", {
        "structure": APT_STRUCTURE,
        "structure_json": json.dumps(APT_STRUCTURE),
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


async def current_affairs(request: Request):
    return templates.TemplateResponse(request, "current_affairs.html")


async def api_ca_content(request: Request):
    """Return raw markdown for a given date, or 404 if not found."""
    date = request.path_params["date"]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return PlainTextResponse("Invalid date format.", status_code=400)
    ca_file = CA_DIR / f"{date}.md"
    if not ca_file.exists():
        return PlainTextResponse("", status_code=404)
    return PlainTextResponse(ca_file.read_text(encoding="utf-8"))


async def api_ca_month(request: Request):
    """Return list of day numbers (int) that have CA content for year/month."""
    try:
        year  = int(request.path_params["year"])
        month = int(request.path_params["month"])
    except ValueError:
        return JSONResponse({"error": "Invalid year/month"}, status_code=400)
    return JSONResponse({"days": _ca_days_for_month(year, month)})


# ---------------------------------------------------------------------------
# Routing table
# ---------------------------------------------------------------------------

routes = [
    Route("/",                              homepage),
    Route("/group1",                        group1),
    Route("/group2",                        group2),
    Route("/current-affairs",              current_affairs),
    Route("/aptitude",                      aptitude),
    Route("/api/ca/content/{date}",         api_ca_content),
    Route("/api/ca/month/{year}/{month}",   api_ca_month),
    Mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static"),
    Mount("/pdfs",   StaticFiles(directory=str(FILES_DIR)),  name="pdfs"),
]

app = Starlette(routes=routes)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    if not os.environ.get("RENDER"):
        print("=" * 50)
        print("  APPSC 2026 Website")
        print("  Open: http://localhost:8000")
        print("  Press Ctrl+C to stop")
        print("=" * 50)
    uvicorn.run(app, host=host, port=port)
