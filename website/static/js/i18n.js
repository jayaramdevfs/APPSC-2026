/* GroupsGuru — Bilingual Support (English + Telugu)
   Usage: window.GG_I18N.t(key), window.GG_I18N.toggleLang()
   Elements with data-i18n="key" are auto-translated on load and toggle.
   Elements with data-i18n-placeholder="key" get their placeholder translated.
   Listen for "gg:langchange" custom event for page-specific re-renders. */
(function () {
  'use strict';

  var TRANSLATIONS = {
    en: {
      /* ── Navigation ────────────────────────────────── */
      'nav.home':             'Home',
      'nav.group1':           'Group I',
      'nav.group2':           'Group II',
      'nav.current_affairs':  'Current Affairs',
      'nav.aptitude':         'Aptitude',
      'nav.telugu':           'Telugu',
      'nav.dashboard':        'Dashboard',
      'nav.pins':             'Pins',
      'nav.login':            'Login',
      'nav.logout':           'Logout',
      'nav.join_now':         'Join Now',
      'nav.change_password':  'Change Password',
      'nav.theme':            'Theme',
      'nav.theme.default':    'Default',
      'nav.theme.black_panther': 'Black Panther',
      'nav.theme.ghost_rider':   'Ghost Rider',
      'nav.theme.varanasi':      'Varanasi',
      'nav.theme.high_contrast': 'High Contrast',
      'nav.theme.retro':         'Retro',
      'nav.music.off':        'Ambient music: Off',
      'nav.music.on':         'Ambient music: On',
      'nav.open_dashboard':   'Open Dashboard',
      'nav.search.placeholder': 'Search syllabus topics…',
      'nav.search.hint':      'Type at least 2 characters to search across all subjects.',
      'nav.search.loading':   'Searching…',
      'nav.search.no_results':'No results found for "{q}".',
      'nav.search.error':     'Search failed. Try again.',

      /* ── Dashboard (logged-in home) ────────────────── */
      'dash.your_prep':       'Your APPSC 2026 prep, at a glance.',
      'dash.group1_prelims':  'Group I Prelims',
      'dash.group2_screening':'Group II Screening',
      'dash.topics_studied':  'Topics Studied',
      'dash.day_streak':      'Day Streak',
      'dash.due_to_revise':   'Due to Revise',
      'dash.mastered':        'Mastered',
      'dash.resume_label':    'Pick up where you left off',
      'dash.continue':        'Continue →',
      'dash.current_affairs': 'Current Affairs',
      'dash.loading_latest':  'Loading latest…',
      'dash.group1_tab':      'Group I',
      'dash.group2_tab':      'Group II',
      'dash.open_ca_library': 'Open Current Affairs Library →',
      'dash.no_ca':           'No current affairs published yet. Check back soon.',

      /* ── Hero (logged-out) ─────────────────────────── */
      'hero.badge':           'ANDHRA PRADESH STATE CIVIL SERVICES',
      'hero.title':           'Ace APPSC 2026',
      'hero.title_accent':    'With Precision.',
      'hero.subtitle':        "India’s most structured APPSC prep platform — syllabus-mapped notes, Pomodoro-powered focus sessions, and real-time progress tracking. Built for Group I and Group II aspirants.",
      'hero.group1_prelims':  'Group I Prelims',
      'hero.group2_screening':'Group II Screening',
      'hero.start_preparing': 'Start Preparing →',
      'hero.login':           'Login',
      'hero.today_ca':        '📰 Today’s Current Affairs',
      'hero.read_full_ca':    'Read full Current Affairs →',
      'hero.topics_mapped':   'Topics Mapped',
      'hero.exam_groups':     'Exam Groups',
      'hero.revision_system': 'Revision System',
      'hero.free':            'Free',
      'hero.always':          'Always',

      /* ── Feature strip ─────────────────────────────── */
      'feat.syllabus_notes':  'Syllabus-Mapped Notes',
      'feat.syllabus_desc':   'Every APPSC topic covered with exam-focused study notes',
      'feat.pomodoro':        'Pomodoro Time Coach',
      'feat.pomodoro_desc':   '25-minute focus sessions with enforced breaks for deep retention',
      'feat.revision_tracker':'1-4-7 Revision Tracker',
      'feat.revision_desc':   'Scientifically timed revision reminders to lock topics in memory',
      'feat.daily_ca':        'Daily Current Affairs',
      'feat.daily_ca_desc':   'Curated AP and national news with APPSC exam relevance tags',

      /* ── Current Affairs page ──────────────────────── */
      'ca.title':             'Current Affairs 2026',
      'ca.subtitle':          "Select a date to read that day’s affairs — dates with content are highlighted in saffron",
      'ca.loading':           'Loading…',
      'ca.loading_content':   'Loading latest…',
      'ca.fetching':          'Fetching latest current affairs…',
      'ca.no_content':        'No current affairs have been published yet.',
      'ca.no_content_yet':    'No content available yet',
      'ca.latest_badge':      'Latest',
      'ca.nearest_to':        'nearest to',
      'ca.load_error':        'Could not load. Please try again.',
      'ca.back':              '← Back',
      'ca.dow.sun': 'Sun', 'ca.dow.mon': 'Mon', 'ca.dow.tue': 'Tue', 'ca.dow.wed': 'Wed',
      'ca.dow.thu': 'Thu', 'ca.dow.fri': 'Fri', 'ca.dow.sat': 'Sat',

      /* ── Dashboard page ────────────────────────────── */
      'dashboard.good_day':         'Good day',
      'dashboard.topics_studied':   'Topics Studied',
      'dashboard.mastered':         'Mastered',
      'dashboard.day_streak':       'Day Streak',
      'dashboard.due_today':        'Due Today',
      'dashboard.curriculum_heatmap':   'Curriculum Heatmap',
      'dashboard.click_to_expand':  'Click to expand — Super-Interactive Syllabus Progress',
      'dashboard.generating':       'Generating Grid...',

      /* ── Group I page ──────────────────────────────── */
      'group1.back':          '← Back to Home',
      'group1.title':         'Group I — Study Portal',
      'group1.subtitle':      'APPSC Gazetted Officers Exam | Prelims • Mains Paper II • Paper III • Paper IV • Paper V',
      'group1.exam_scheme':   'Exam Scheme',
      'group1.official_pattern': 'Official Pattern',

      /* ── Group II page ─────────────────────────────── */
      'group2.back':          '← Back to Home',
      'group2.title':         'Group II — Study Portal',
      'group2.subtitle':      'APPSC Non-Gazetted Officers Exam | Screening • Mains',
      'group2.exam_scheme':   'Exam Scheme',
      'group2.official_pattern': 'Official Pattern',

      /* ── Common ────────────────────────────────────── */
      'common.back':          '← Back',
      'common.subject':       'Subject',
      'common.questions':     'No. of Questions',
      'common.duration_min':  'Duration Minutes',
      'common.max_marks':     'Maximum Marks',
      'common.qualifying':    'Qualifying Nature',
      'common.paper':         'Paper',
      'common.duration':      'Duration',

      /* ── Days & Months (arrays, used by JS) ─────────── */
      'days.long':   ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
      'months.long': ['January','February','March','April','May','June','July','August','September','October','November','December'],
      'months.short':['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
    },

    te: {
      /* ── Navigation ────────────────────────────────── */
      'nav.home':             'హోమ్',
      'nav.group1':           'గ్రూప్ I',
      'nav.group2':           'గ్రూప్ II',
      'nav.current_affairs':  'కరెంట్ అఫైర్స్',
      'nav.aptitude':         'అప్టిట్యూడ్',
      'nav.telugu':           'తెలుగు',
      'nav.dashboard':        'డాష్‌బోర్డ్',
      'nav.pins':             'పిన్స్',
      'nav.login':            'లాగిన్',
      'nav.logout':           'లాగ్అవుట్',
      'nav.join_now':         'చేరండి',
      'nav.change_password':  'పాస్‌వర్డ్ మార్చండి',
      'nav.theme':            'థీమ్',
      'nav.theme.default':    'డిఫాల్ట్',
      'nav.theme.black_panther': 'బ్లాక్ పాంథర్',
      'nav.theme.ghost_rider':   'ఘోస్ట్ రైడర్',
      'nav.theme.varanasi':      'వారణాసి',
      'nav.theme.high_contrast': 'హై కాంట్రాస్ట్',
      'nav.theme.retro':         'రెట్రో',
      'nav.music.off':        'సంగీతం: ఆఫ్',
      'nav.music.on':         'సంగీతం: ఆన్',
      'nav.open_dashboard':   'డాష్‌బోర్డ్ తెరవండి',
      'nav.search.placeholder': 'సిలబస్ విషయాలు వెతకండి…',
      'nav.search.hint':      'అన్ని విషయాలలో వెతకడానికి కనీసం 2 అక్షరాలు టైప్ చేయండి.',
      'nav.search.loading':   'వెతుకుతోంది…',
      'nav.search.no_results':'"{q}" కోసం ఫలితాలు లేవు.',
      'nav.search.error':     'వెతకడం విఫలమైంది. మళ్ళీ ప్రయత్నించండి.',

      /* ── Dashboard (logged-in home) ────────────────── */
      'dash.your_prep':       'మీ APPSC 2026 సన్నద్ధత, ఒక చూపులో.',
      'dash.group1_prelims':  'గ్రూప్ I ప్రిలిమ్స్',
      'dash.group2_screening':'గ్రూప్ II స్క్రీనింగ్',
      'dash.topics_studied':  'చదివిన విషయాలు',
      'dash.day_streak':      'రోజుల వరుస',
      'dash.due_to_revise':   'రివిజన్ చేయవలసినవి',
      'dash.mastered':        'నేర్చుకున్నవి',
      'dash.resume_label':    'మీరు ఆపిన చోటి నుండి',
      'dash.continue':        'కొనసాగించు →',
      'dash.current_affairs': 'కరెంట్ అఫైర్స్',
      'dash.loading_latest':  'లోడ్ అవుతోంది…',
      'dash.group1_tab':      'గ్రూప్ I',
      'dash.group2_tab':      'గ్రూప్ II',
      'dash.open_ca_library': 'కరెంట్ అఫైర్స్ లైబ్రరీ తెరవండి →',
      'dash.no_ca':           'ఇంకా కరెంట్ అఫైర్స్ ప్రచురించబడలేదు. తర్వాత మళ్ళీ చెక్ చేయండి.',

      /* ── Hero (logged-out) ─────────────────────────── */
      'hero.badge':           'ఆంధ్రప్రదేశ్ స్టేట్ సివిల్ సర్వీసెస్',
      'hero.title':           'APPSC 2026 జయించండి',
      'hero.title_accent':    'ఖచ్చితంగా.',
      'hero.subtitle':        'భారతదేశపు అత్యంత క్రమబద్ధమైన APPSC సన్నద్ధత వేదిక — సిలబస్ నోట్స్, పొమోడోరో ఫోకస్ సెషన్స్, మరియు రియల్-టైమ్ ప్రోగ్రెస్ ట్రాకింగ్. గ్రూప్ I మరియు గ్రూప్ II విద్యార్థుల కోసం నిర్మించబడింది.',
      'hero.group1_prelims':  'గ్రూప్ I ప్రిలిమ్స్',
      'hero.group2_screening':'గ్రూప్ II స్క్రీనింగ్',
      'hero.start_preparing': 'సన్నద్ధత ప్రారంభించండి →',
      'hero.login':           'లాగిన్',
      'hero.today_ca':        '📰 నేటి కరెంట్ అఫైర్స్',
      'hero.read_full_ca':    'పూర్తి కరెంట్ అఫైర్స్ చదవండి →',
      'hero.topics_mapped':   'మ్యాప్ చేసిన విషయాలు',
      'hero.exam_groups':     'పరీక్షా గ్రూపులు',
      'hero.revision_system': 'రివిజన్ విధానం',
      'hero.free':            'ఉచితం',
      'hero.always':          'ఎప్పుడూ',

      /* ── Feature strip ─────────────────────────────── */
      'feat.syllabus_notes':  'సిలబస్ నోట్స్',
      'feat.syllabus_desc':   'ప్రతి APPSC విషయం పరీక్ష-కేంద్రిత నోట్స్తో కవర్ చేయబడింది',
      'feat.pomodoro':        'పొమోడోరో టైమ్ కోచ్',
      'feat.pomodoro_desc':   '25-నిమిషాల ఫోకస్ సెషన్స్ లోతైన నిలుపుదల కోసం విరామాలతో',
      'feat.revision_tracker':'1-4-7 రివిజన్ ట్రాకర్',
      'feat.revision_desc':   'విషయాలు మెమరీలో నిలిపేందుకు శాస్త్రీయ రివిజన్ రిమైండర్లు',
      'feat.daily_ca':        'రోజువారీ కరెంట్ అఫైర్స్',
      'feat.daily_ca_desc':   'APPSC పరీక్ష సంబంధిత AP మరియు జాతీయ వార్తలు',

      /* ── Current Affairs page ──────────────────────── */
      'ca.title':             'కరెంట్ అఫైర్స్ 2026',
      'ca.subtitle':          'ఆ రోజు అఫైర్స్ చదవడానికి తేదీ ఎంచుకోండి — కంటెంట్ ఉన్న తేదీలు హైలైట్ చేయబడతాయి',
      'ca.loading':           'లోడ్ అవుతోంది…',
      'ca.loading_content':   'తాజా లోడ్ అవుతోంది…',
      'ca.fetching':          'తాజా కరెంట్ అఫైర్స్ తీసుకొస్తోంది…',
      'ca.no_content':        'ఇంకా కరెంట్ అఫైర్స్ ప్రచురించబడలేదు.',
      'ca.no_content_yet':    'ఇంకా కంటెంట్ లేదు',
      'ca.latest_badge':      'తాజా',
      'ca.nearest_to':        'సమీపంలో',
      'ca.load_error':        'లోడ్ కాలేదు. మళ్ళీ ప్రయత్నించండి.',
      'ca.back':              '← వెనుకకు',
      'ca.dow.sun': 'ఆది', 'ca.dow.mon': 'సోమ', 'ca.dow.tue': 'మంగ', 'ca.dow.wed': 'బుధ',
      'ca.dow.thu': 'గురు', 'ca.dow.fri': 'శుక్ర', 'ca.dow.sat': 'శని',

      /* ── Dashboard page ────────────────────────────── */
      'dashboard.good_day':        'నమస్కారం',
      'dashboard.topics_studied':  'చదివిన విషయాలు',
      'dashboard.mastered':        'నేర్చుకున్నవి',
      'dashboard.day_streak':      'రోజుల వరుస',
      'dashboard.due_today':       'నేడు రివిజన్',
      'dashboard.curriculum_heatmap':  'కరిక్యులమ్ హీట్‌మ్యాప్',
      'dashboard.click_to_expand': 'విస్తరించడానికి క్లిక్ చేయండి — సిలబస్ ప్రోగ్రెస్',
      'dashboard.generating':      'గ్రిడ్ తయారవుతోంది...',

      /* ── Group I page ──────────────────────────────── */
      'group1.back':          '← హోమ్‌కి తిరిగి',
      'group1.title':         'గ్రూప్ I — అధ్యయన పోర్టల్',
      'group1.subtitle':      'APPSC గెజిటెడ్ అధికారుల పరీక్ష | ప్రిలిమ్స్ • మెయిన్స్ పేపర్ II • III • IV • V',
      'group1.exam_scheme':   'పరీక్షా విధానం',
      'group1.official_pattern': 'అధికారిక నమూనా',

      /* ── Group II page ─────────────────────────────── */
      'group2.back':          '← హోమ్‌కి తిరిగి',
      'group2.title':         'గ్రూప్ II — అధ్యయన పోర్టల్',
      'group2.subtitle':      'APPSC నాన్-గెజిటెడ్ అధికారుల పరీక్ష | స్క్రీనింగ్ • మెయిన్స్',
      'group2.exam_scheme':   'పరీక్షా విధానం',
      'group2.official_pattern': 'అధికారిక నమూనా',

      /* ── Common ────────────────────────────────────── */
      'common.back':          '← వెనుకకు',
      'common.subject':       'విషయం',
      'common.questions':     'ప్రశ్నల సంఖ్య',
      'common.duration_min':  'వ్యవధి (నిమిషాలు)',
      'common.max_marks':     'గరిష్ట మార్కులు',
      'common.qualifying':    'అర్హత స్వభావం',
      'common.paper':         'పేపర్',
      'common.duration':      'వ్యవధి',

      /* ── Days & Months (arrays, used by JS) ─────────── */
      'days.long':   ['ఆదివారం','సోమవారం','మంగళవారం','బుధవారం','గురువారం','శుక్రవారం','శనివారం'],
      'months.long': ['జనవరి','ఫిబ్రవరి','మార్చి','ఏప్రిల్','మే','జూన్','జూలై','ఆగస్టు','సెప్టెంబర్','అక్టోబర్','నవంబర్','డిసెంబర్'],
      'months.short':['జన','ఫిబ్ర','మార్చి','ఏప్రి','మే','జూన్','జూలై','ఆగ','సెప్ట','అక్టో','నవ','డిసె'],
    }
  };

  var _lang = localStorage.getItem('gg_lang') || 'en';

  function t(key) {
    var dict = TRANSLATIONS[_lang] || TRANSLATIONS.en;
    if (dict[key] !== undefined) return dict[key];
    if (TRANSLATIONS.en[key] !== undefined) return TRANSLATIONS.en[key];
    return key;
  }

  function applyLang() {
    /* Translate textContent */
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var val = t(el.dataset.i18n);
      if (typeof val === 'string') el.textContent = val;
    });
    /* Translate innerHTML (use sparingly, only when HTML entities needed) */
    document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      var val = t(el.dataset.i18nHtml);
      if (typeof val === 'string') el.innerHTML = val;
    });
    /* Translate placeholder attributes */
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      var val = t(el.dataset.i18nPlaceholder);
      if (typeof val === 'string') el.placeholder = val;
    });
    /* Update <html lang> */
    document.documentElement.lang = _lang === 'te' ? 'te' : 'en';
    /* Update toggle button label */
    var btn = document.getElementById('lang-toggle');
    if (btn) {
      var lbl = btn.querySelector('.lang-btn-label');
      if (lbl) lbl.textContent = _lang === 'en' ? 'తెలుగు' : 'English';
    }
    /* Notify page-specific scripts */
    document.dispatchEvent(new CustomEvent('gg:langchange', { detail: { lang: _lang } }));
  }

  function toggleLang() {
    _lang = _lang === 'en' ? 'te' : 'en';
    localStorage.setItem('gg_lang', _lang);
    applyLang();
  }

  function getLang() { return _lang; }

  window.GG_I18N = { t: t, applyLang: applyLang, toggleLang: toggleLang, lang: getLang };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyLang);
  } else {
    applyLang();
  }
})();
