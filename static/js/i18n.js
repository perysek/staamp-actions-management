/* ──────────────────────────────────────────────────────────────────────────
   i18n.js — client-side Polish ⇄ English UI overlay.

   The app is authored in Polish (server-rendered + JS-rendered). This layer
   lets the user flip the whole GUI to English (and back) instantly, with no
   page reload and no server round-trip.

   How it works
   ------------
   • DICT maps Polish UI strings → English (exact, whole-text-node match).
   • SUBSTR is a small fallback for text nodes mixed with dynamic data
     (footers, "added: 5, updated: 3" banners, confirm sentences with a title).
   • The ORIGINAL Polish of every touched node is captured once in a WeakMap,
     so toggling back to Polish simply restores the original — fully reversible.
   • A MutationObserver re-translates content rendered later by app JS
     (toasts, tables, modals, the Gantt chart).

   Preference is stored in localStorage('staamp_lang'); default 'pl'.
   Public API: window.I18n.set('en'|'pl'), .toggle(), .current().
   ────────────────────────────────────────────────────────────────────────── */
(function () {
    'use strict';

    var STORE_KEY = 'staamp_lang';
    var ATTRS = ['placeholder', 'title', 'aria-label'];

    /* ── Exact PL → EN (whole trimmed text-node value, or attribute value) ──
       Strings identical in both languages (Status, IP, Start, Gantt, MOSYS,
       System, ID MOSYS…) are intentionally omitted — leaving them out means
       fewer chances for an accidental match. */
    var DICT = {
        /* Navigation / app shell */
        'Zarządzanie działaniami': 'Action Management',
        'Pulpit': 'Dashboard',
        'Działania': 'Actions',
        'Oś czasu': 'Timeline',
        'Użytkownicy': 'Users',
        'Pracownicy': 'Employees',
        'Role i uprawnienia': 'Roles & permissions',
        'Dziennik zdarzeń': 'Audit log',
        'Wyloguj': 'Log out',
        'Przejdź do treści': 'Skip to content',
        'Nawigacja główna': 'Main navigation',
        'Otwórz menu': 'Open menu',
        'Zamknij': 'Close',

        /* Dashboard */
        'Przegląd działań według statusu': 'Overview of actions by status',
        'Wszystkie działania': 'All actions',
        'Wszystkie': 'All',
        'Brak działań do wyświetlenia.': 'No actions to display.',

        /* Common buttons / actions */
        '+ Nowe działanie': '+ New action',
        '+ Podzadanie': '+ Subtask',
        '+ Nowy użytkownik': '+ New user',
        '+ Nowa rola': '+ New role',
        '+ Dodaj ręcznie': '+ Add manually',
        'Edytuj': 'Edit',
        'Usuń': 'Delete',
        'Anuluj': 'Cancel',
        'Zapisz': 'Save',
        'Zapisz zmiany': 'Save changes',
        'Utwórz': 'Create',
        'Szczegóły': 'Details',
        'Gantt': 'Gantt',
        'Potwierdź': 'Confirm',

        /* Status labels (items) */
        'Otwarte': 'Open',
        'W toku': 'In progress',
        'Wstrzymane': 'On hold',
        'Zakończone': 'Done',
        'Anulowane': 'Cancelled',

        /* Status labels (subtasks) */
        'Nie rozpoczęte': 'Not started',
        'Zablokowane': 'Blocked',

        /* Type labels */
        'Zadanie': 'Task',
        'Projekt': 'Project',
        'Działanie': 'Action',
        'Cel': 'Goal',

        /* Table headers / field labels */
        'Typ': 'Type',
        'Tytuł': 'Title',
        'Termin': 'Due date',
        'Odpowiedzialni': 'Responsible',
        'Odpowiedzialny': 'Responsible',
        'Podzadania': 'Subtasks',
        'Podzadanie': 'Subtask',
        'Koniec': 'End',
        'Opis': 'Description',
        'Imię i nazwisko': 'Full name',
        'Imię': 'First name',
        'Nazwisko': 'Surname',
        'Rola': 'Role',
        'Nr prac.': 'Emp. no.',
        'Nr pracownika': 'Emp. number',
        'Ostatnie logowanie': 'Last login',
        'Nazwa systemowa': 'System name',
        'Wyświetlana nazwa': 'Display name',
        'Dostęp do modułów': 'Module access',
        'Czas': 'Time',
        'Zdarzenie': 'Event',
        'Użytkownik': 'User',
        'Nazwisko i imię': 'Surname and first name',
        'Konto użytkownika': 'User account',

        /* Empty / loading states */
        'Ładowanie…': 'Loading…',
        'Ładowanie podzadań…': 'Loading subtasks…',
        'Brak działań': 'No actions',
        'Brak użytkowników': 'No users',
        'Brak podzadań': 'No subtasks',
        'Brak zdarzeń': 'No events',
        'Brak': 'None',
        'brak': 'none',
        'Brak podzadań z datami do wyświetlenia na osi czasu.': 'No subtasks with dates to display on the timeline.',
        'Brak pracowników. Kliknij "Synchronizuj z MOSYS" aby zaimportować.': 'No employees. Click "Sync with MOSYS" to import.',
        'Brak aktywnych użytkowników.': 'No active users.',

        /* Search placeholders */
        'Szukaj…': 'Search…',
        'Szukaj...': 'Search...',

        /* Items: list / detail / form */
        'Zadania, projekty, działania i cele': 'Tasks, projects, actions and goals',
        'Szczegóły działania': 'Action details',
        'Pokaż oś czasu': 'Show timeline',
        'Odpowiedzialni (działanie)': 'Responsible (action)',
        'Nowe działanie': 'New action',
        'Edytuj działanie': 'Edit action',
        'Utwórz zadanie, projekt, działanie lub cel': 'Create a task, project, action or goal',
        'Krótki tytuł działania': 'Short action title',
        'Zaznacz osoby odpowiedzialne za to działanie.': 'Select the people responsible for this action.',

        /* Items: subtask modal / colour picker / notifications */
        'Nowe podzadanie': 'New subtask',
        'Edytuj podzadanie': 'Edit subtask',
        'Usuń podzadanie': 'Delete subtask',
        'Usuń działanie': 'Delete action',
        'Tytuł podzadania': 'Subtask title',
        'Zmień kolor podzadania': 'Change subtask colour',
        'Kolor podzadania': 'Subtask colour',
        'Domyślny (wg statusu)': 'Default (by status)',
        '— brak —': '— none —',
        'Tytuł jest wymagany': 'Title is required',
        'Zaktualizowano status': 'Status updated',
        'Zapisano': 'Saved',
        'Zapisano podzadanie': 'Subtask saved',
        'Dodano podzadanie': 'Subtask added',
        'Usunięto działanie': 'Action deleted',
        'Usunięto podzadanie': 'Subtask deleted',
        'Błąd usuwania': 'Delete error',
        'Błąd zapisu': 'Save error',
        'Błąd tworzenia': 'Create error',
        'Błąd zmiany statusu': 'Status change error',
        'Błąd zmiany koloru': 'Colour change error',

        /* Timeline */
        'Wybierz działanie, aby zobaczyć wykres Gantta jego podzadań': 'Select an action to see the Gantt chart of its subtasks',
        'Wykres Gantta podzadań ·': 'Subtask Gantt chart ·',
        'Dni': 'Days',
        'Tygodnie': 'Weeks',
        'Miesiące': 'Months',

        /* Users */
        'Zarządzanie kontami użytkowników systemu': 'Management of system user accounts',
        'Nowy użytkownik': 'New user',
        'Edytuj użytkownika': 'Edit user',
        'Utwórz konto na podstawie numeru pracownika': 'Create an account from an employee number',
        'Edycja konta użytkownika': 'Editing user account',
        'Nr pracownika *': 'Emp. number *',
        'Imię i nazwisko *': 'Full name *',
        'Rola *': 'Role *',
        'Powiązany pracownik': 'Linked employee',
        'Konto aktywne': 'Account active',
        '— zostanie uzupełnione automatycznie —': '— filled in automatically —',
        '— wybierz rolę —': '— select a role —',
        'Hasło tymczasowe zostanie wygenerowane automatycznie. Pracownik będzie musiał je zmienić przy pierwszym logowaniu.': 'A temporary password will be generated automatically. The employee will have to change it at first login.',
        'Utwórz użytkownika': 'Create user',
        'Aktywny': 'Active',
        'Nieaktywny': 'Inactive',
        'Aktywuj': 'Activate',
        'Dezaktywuj': 'Deactivate',
        'Reset hasła': 'Password reset',
        'Ustawiasz nowe hasło dla:': 'Setting a new password for:',
        'Nowe hasło (min. 8 znaków)': 'New password (min. 8 characters)',
        'Ustaw hasło': 'Set password',
        '✓ Pracownik odnaleziony': '✓ Employee found',
        '✗ Nie znaleziono pracownika lub konto już istnieje': '✗ Employee not found or account already exists',
        'Uzupełnij wszystkie pola.': 'Fill in all fields.',
        'Błąd tworzenia użytkownika.': 'Error creating user.',
        'Błąd aktualizacji.': 'Update error.',
        'Hasło musi mieć co najmniej 8 znaków': 'Password must be at least 8 characters',
        'Błąd': 'Error',

        /* Roles */
        'Role': 'Roles',
        'Zarządzanie rolami i uprawnieniami do modułów': 'Management of roles and module permissions',
        'Nowa rola': 'New role',
        'Edytuj rolę': 'Edit role',
        'Zdefiniuj rolę i przydziel uprawnienia do modułów': 'Define a role and assign module permissions',
        'Nazwa systemowa *': 'System name *',
        'Wyświetlana nazwa *': 'Display name *',
        'Tylko małe litery i podkreślenia': 'Lowercase letters and underscores only',
        'np. kierownik': 'e.g. supervisor',
        'np. Kierownik zmiany': 'e.g. Shift supervisor',
        'Ograniczenia': 'Restrictions',
        'Utwórz rolę': 'Create role',
        'Edytuj uprawnienia': 'Edit permissions',
        'Systemowa': 'System',
        'Błąd tworzenia roli.': 'Error creating role.',
        'Błąd zapisu.': 'Save error.',
        'Usuń rolę': 'Delete role',
        'Usunięto rolę': 'Role deleted',
        'Błąd usuwania roli': 'Error deleting role',
        /* module / flag display names */
        'Administracja': 'Administration',
        'Widok: tylko z moim podzadaniem': 'View: only with my subtask',
        'Edycja: tylko moje podzadania': 'Edit: only my subtasks',
        'Widok: tylko pozycje z moim podzadaniem': 'View: only items with my subtask',
        'Edycja: tylko moje podzadania (status)': 'Edit: only my subtasks (status)',

        /* Employees */
        'Zarządzanie pracownikami i powiązania z MOSYS': 'Employee management and MOSYS links',
        'Synchronizuj z MOSYS': 'Sync with MOSYS',
        'Synchronizuję…': 'Syncing…',
        'Nowy pracownik': 'New employee',
        'Edytuj pracownika': 'Edit employee',
        'Nazwisko *': 'Surname *',
        'opcjonalnie': 'optional',
        'Nazwisko jest wymagane': 'Surname is required',
        'Błąd połączenia': 'Connection error',
        'nieznany błąd': 'unknown error',
        'Usuń pracownika': 'Delete employee',
        'Usunięto pracownika': 'Employee deleted',

        /* Audit log */
        'Ostatnie zdarzenia systemowe (do 500)': 'Recent system events (up to 500)',
        'Logowanie': 'Login',
        'Nieudane logowanie': 'Failed login',
        'Wylogowanie': 'Logout',
        'Zmiana hasła': 'Password change',
        'Ustawienie pierwszego hasła': 'First password set',
        'Utworzenie użytkownika': 'User created',
        'Edycja użytkownika': 'User edited',
        'Zmiana aktywności konta': 'Account activity change',
        'Utworzenie pracownika': 'Employee created',
        'Edycja pracownika': 'Employee edited',
        'Usunięcie pracownika': 'Employee deleted',
        'Synchronizacja MOSYS': 'MOSYS sync',
        'Utworzenie roli': 'Role created',
        'Edycja roli': 'Role edited',
        'Usunięcie roli': 'Role deleted',
        'Utworzenie pozycji': 'Item created',
        'Edycja pozycji': 'Item edited',
        'Usunięcie pozycji': 'Item deleted',
        'Utworzenie podzadania': 'Subtask created',
        'Edycja podzadania': 'Subtask edited',
        'Usunięcie podzadania': 'Subtask deleted',
        'Zmiana statusu podzadania': 'Subtask status change',

        /* Auth — login ('Logowanie' / 'Zmiana hasła' are defined in the Audit block) */
        'Zarządzanie działaniami STAAMP': 'STAAMP Action Management',
        'Hasło': 'Password',
        'Zapamiętaj mnie': 'Remember me',
        'Zaloguj się': 'Sign in',
        'Pierwsze logowanie': 'First login',
        'Pierwsze logowanie.': 'First login.',
        'Nowe hasło': 'New password',
        'Potwierdź hasło': 'Confirm password',
        'Potwierdź nowe hasło': 'Confirm new password',
        'Aktualne hasło': 'Current password',
        'min. 8 znaków': 'min. 8 characters',
        'Ustaw hasło i zaloguj': 'Set password and sign in',
        '← Wróć do logowania': '← Back to login',
        'Wróć do logowania': 'Back to login',
        'Nie pamiętam hasła': 'Forgot my password',
        'Numer pracownika musi zaczynać się od 9 (4 cyfry)': 'Employee number must start with 9 (4 digits)',
        'Zmień hasło': 'Change password',
        'Proszę ustawić własne hasło, aby kontynuować korzystanie z systemu.': 'Please set your own password to continue using the system.',

        /* Auth — password reset flow */
        'Resetowanie hasła': 'Password reset',
        'Ustaw nowe hasło': 'Set a new password',
        'Generuj link': 'Generate link',
        'Link do zresetowania hasła (ważny 1 godzinę):': 'Password reset link (valid for 1 hour):',
        'Podaj numer pracownika, aby wygenerować link do zresetowania hasła.': 'Enter the employee number to generate a password reset link.',
        'Zarządzanie działaniami STAAMP ': 'STAAMP Action Management ',

        /* Flash / service messages */
        'Wylogowano pomyślnie': 'Logged out successfully',
        'Nieprawidłowe żądanie zmiany hasła.': 'Invalid password change request.',
        'Hasło musi mieć co najmniej 8 znaków.': 'The password must be at least 8 characters.',
        'Hasła nie są identyczne.': 'The passwords do not match.',
        'Hasła nie są identyczne': 'The passwords do not match',
        'Nowe hasła nie są identyczne': 'The new passwords do not match',
        'Hasło zostało ustawione. Witaj w systemie!': 'Your password has been set. Welcome!',
        'Hasło zostało zmienione': 'Your password has been changed',
        'Hasło zostało zmienione. Możesz się teraz zalogować.': 'Your password has been changed. You can now sign in.',
        'Jeśli adres e-mail istnieje w systemie, link do resetowania hasła jest widoczny poniżej.': 'If the email exists in the system, the password reset link is shown below.',
        'Link wygasł lub został już wykorzystany.': 'The link has expired or has already been used.',
        'Pozycja nie istnieje': 'Item does not exist',
        'Rola nie istnieje': 'Role does not exist',
        'Użytkownik nie istnieje': 'User does not exist',
        'Nie możesz edytować konta właściciela': 'You cannot edit the owner account',
        'Musisz być zalogowany': 'You must be logged in',
        'Musisz być zalogowany, aby uzyskać dostęp do tej strony.': 'You must be logged in to access this page.',
        'Brak uprawnień': 'No permission',
        'Konto jest nieaktywne. Skontaktuj się z administratorem.': 'The account is inactive. Please contact an administrator.',
        'Nieprawidłowe aktualne hasło': 'Incorrect current password',
        'Nieprawidłowy e-mail lub hasło': 'Invalid email or password',
        'Nieprawidłowy nr pracownika lub hasło': 'Invalid employee number or password',
        'Nieprawidłowy nr pracownika — numer musi zaczynać się od 9': 'Invalid employee number — it must start with 9'
    };

    /* ── Substring fallback — only applied when a node has NO exact match.
       Used for text nodes mixed with dynamic data. Order matters: longer /
       more specific phrases first so they win over their own prefixes. ── */
    var SUBSTR = [
        ['wewnętrzne narzędzie produkcyjne', 'internal production tool'],
        ['wewnętrzne narzędzie', 'internal tool'],
        ['Zarządzanie działaniami', 'Action Management'],
        ['Wszystkie podzadania zostaną usunięte.', 'All subtasks will be deleted.'],
        ['Czy na pewno usunąć', 'Are you sure you want to delete'],
        ['Użytkownicy z tą rolą utracą dostęp.', 'Users with this role will lose access.'],
        ['Usunąć rolę', 'Delete role'],
        ['Usunąć pracownika', 'Delete employee'],
        ['Synchronizacja zakończona — dodano:', 'Sync complete — added:'],
        [', zaktualizowano:', ', updated:'],
        [', z MOSYS:', ', from MOSYS:'],
        ['Błąd synchronizacji:', 'Sync error:'],
        ['Brak dostępu do modułu:', 'No access to module:'],
        ['Teraz ', 'Now ']
    ];

    /* ── State ── */
    var lang = 'pl';
    try { lang = localStorage.getItem(STORE_KEY) || 'pl'; } catch (e) { /* private mode */ }

    var origText = new WeakMap();   // textNode -> original Polish nodeValue
    var origAttr = new WeakMap();   // element  -> { attrName: original Polish value }
    var observer = null;

    /* ── Translation helpers ── */
    function exact(pl) {
        return Object.prototype.hasOwnProperty.call(DICT, pl) ? DICT[pl] : null;
    }
    function substr(pl) {
        var out = pl, changed = false;
        for (var i = 0; i < SUBSTR.length; i++) {
            if (out.indexOf(SUBSTR[i][0]) !== -1) {
                out = out.split(SUBSTR[i][0]).join(SUBSTR[i][1]);
                changed = true;
            }
        }
        return changed ? out : null;
    }
    function translate(pl) {
        var e = exact(pl);
        return e !== null ? e : substr(pl);
    }

    /* ── Text node ── */
    function processText(node) {
        var raw = node.nodeValue;
        if (!raw) return;
        var trimmed = raw.trim();
        if (!trimmed) return;

        if (!origText.has(node)) {
            if (translate(trimmed) === null) return;   // not translatable — don't track
            origText.set(node, raw);
        }

        var original = origText.get(node);
        var target;
        if (lang === 'en') {
            var en = translate(original.trim());
            if (en === null) return;
            target = original.replace(original.trim(), en);
        } else {
            target = original;                          // restore Polish
        }
        if (node.nodeValue !== target) node.nodeValue = target;
    }

    /* ── Element attributes ── */
    function processAttrs(el) {
        if (!el || el.nodeType !== 1 || !el.getAttribute) return;
        for (var i = 0; i < ATTRS.length; i++) {
            var a = ATTRS[i];
            if (!el.hasAttribute(a)) continue;
            var current = el.getAttribute(a);
            if (!current) continue;

            var store = origAttr.get(el);
            if (!store || !Object.prototype.hasOwnProperty.call(store, a)) {
                if (exact(current.trim()) === null) continue;   // attrs: exact only
                if (!store) { store = {}; origAttr.set(el, store); }
                store[a] = current;
            }

            var original = origAttr.get(el)[a];
            var target;
            if (lang === 'en') {
                var en = exact(original.trim());
                if (en === null) continue;
                target = en;
            } else {
                target = original;
            }
            if (el.getAttribute(a) !== target) el.setAttribute(a, target);
        }
    }

    /* ── Walk a subtree (text + attributes), skipping script/style ── */
    function processTree(node) {
        if (node.nodeType === 3) { processText(node); return; }
        if (node.nodeType !== 1) return;

        processAttrs(node);
        var attrEls = node.querySelectorAll('[placeholder],[title],[aria-label]');
        for (var i = 0; i < attrEls.length; i++) processAttrs(attrEls[i]);

        var walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, {
            acceptNode: function (n) {
                var p = n.parentNode;
                if (!p) return NodeFilter.FILTER_REJECT;
                var t = p.nodeName;
                return (t === 'SCRIPT' || t === 'STYLE' || t === 'NOSCRIPT')
                    ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
            }
        });
        var tn;
        while ((tn = walker.nextNode())) processText(tn);
    }

    /* ── Apply to whole document, with the observer paused to avoid feedback ── */
    function applyAll() {
        if (observer) observer.disconnect();
        processTree(document.body);
        if (observer) { observer.takeRecords(); startObserving(); }
    }

    function startObserving() {
        observer.observe(document.body, {
            childList: true, subtree: true, characterData: true,
            attributes: true, attributeFilter: ATTRS
        });
    }

    function handleMutations(records) {
        observer.disconnect();
        for (var i = 0; i < records.length; i++) {
            var m = records[i];
            if (m.type === 'childList') {
                for (var j = 0; j < m.addedNodes.length; j++) processTree(m.addedNodes[j]);
            } else if (m.type === 'characterData') {
                processText(m.target);
            } else if (m.type === 'attributes') {
                processAttrs(m.target);
            }
        }
        observer.takeRecords();
        startObserving();
    }

    /* ── UI: keep the PL/EN toggle buttons in sync ── */
    function updateButtons() {
        var opts = document.querySelectorAll('.lang-opt');
        for (var i = 0; i < opts.length; i++) {
            var on = opts[i].getAttribute('data-lang') === lang;
            opts[i].classList.toggle('active', on);
            opts[i].setAttribute('aria-pressed', on ? 'true' : 'false');
        }
    }

    /* ── Public API ── */
    function setLang(next) {
        if (next !== 'pl' && next !== 'en') return;
        if (next === lang) { updateButtons(); return; }
        lang = next;
        try { localStorage.setItem(STORE_KEY, lang); } catch (e) { /* ignore */ }
        document.documentElement.setAttribute('lang', lang);
        updateButtons();
        applyAll();
    }

    window.I18n = {
        set: setLang,
        toggle: function () { setLang(lang === 'pl' ? 'en' : 'pl'); },
        current: function () { return lang; }
    };

    /* ── Init (script runs at end of <body>, so the DOM above is ready) ── */
    function init() {
        observer = new MutationObserver(handleMutations);
        document.documentElement.setAttribute('lang', lang);
        updateButtons();
        startObserving();
        if (lang === 'en') applyAll();   // Polish is the default render — only translate when needed
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
