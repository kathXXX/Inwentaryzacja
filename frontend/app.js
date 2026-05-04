const API_URL = "https://web-production-53ca6.up.railway.app";

// ------------------ UI RENDER ------------------

function renderUI() {
    const app = document.getElementById("app");

    if (!token) {
        renderLogin(app);
        return;
    }

    if (userRole === "student") renderStudent(app);
    if (userRole === "nauczyciel") renderTeacher(app);
    if (userRole === "administrator") renderAdmin(app);
}

function renderLogin(app) {
    app.innerHTML = `
        <h2>Logowanie</h2>
        <input id="login_username" placeholder="Username">
        <input id="login_password" type="password" placeholder="Password">
        <button onclick="login()">Zaloguj</button>
    `;
}

let token = null;
let userRole = null;

const authHeaders = () => ({
    "Authorization": `Bearer ${token}`
});

const jsonAuthHeaders = () => ({
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`
});

async function login() {
    const username = document.getElementById("login_username").value;
    const password = document.getElementById("login_password").value;

    const res = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Błąd logowania");
        return;
    }

    token = data.access_token;

    if (!token) {
        alert("Backend nie zwrócił tokena");
        return;
    }

    const payload = JSON.parse(atob(token.split('.')[1]));
    userRole = payload.role;

    renderUI();
}

// ------------------ STUDENT ------------------

function renderStudent(app) {
    app.innerHTML = `
        <h2>Student</h2>

        <button onclick="loadAvailability()">Pokaż dostępność</button>
        <ul id="availability"></ul>

        <h3>Złóż wniosek</h3>
        <input id="loan_item_id" placeholder="Item ID">
        <input id="loan_user_id" placeholder="User ID">
        <button onclick="requestLoan()">Wyślij</button>
    `;
}

// ------------------ NAUCZYCIEL ------------------

function renderTeacher(app) {
    app.innerHTML = `
        <h2>Nauczyciel</h2>

        <button onclick="loadAvailability()">Dostępność</button>
        <ul id="availability"></ul>

        <h3>Oczekujące wnioski</h3>
        <button onclick="loadPendingLoans()">Pokaż</button>
        <ul id="pending"></ul>

        <h3>Zatwierdź wniosek</h3>
        <input id="approve_id" placeholder="Loan ID">
        <button onclick="approveLoan()">Zatwierdź</button>

        <h3>Wypożycz dla siebie</h3>
        <input id="teacher_item_id" placeholder="Item ID">
        <input id="teacher_user_id" placeholder="User ID">
        <button onclick="teacherLoan()">Wypożycz</button>

        <h3>Zwrot</h3>
        <input id="return_id" placeholder="Loan ID">
        <button onclick="returnLoan()">Zwróć</button>
    `;
}

// ------------------ ADMIN ------------------

function renderAdmin(app) {
    app.innerHTML = `
        <h2>Administrator</h2>

        <button onclick="loadAvailability()">Dostępność</button>
        <ul id="availability"></ul>

        <h3>Oczekujące wnioski</h3>
        <button onclick="loadPendingLoans()">Pokaż</button>
        <ul id="pending"></ul>

        <h3>Zatwierdź wniosek</h3>
        <input id="approve_id" placeholder="Loan ID">
        <button onclick="approveLoan()">Zatwierdź</button>

        <h3>Zwrot</h3>
        <input id="return_id" placeholder="Loan ID">
        <button onclick="returnLoan()">Zwróć</button>

        <h3>Dodaj przedmiot</h3>
        <input id="nazwa" placeholder="Nazwa">
        <input id="kategoria" placeholder="Kategoria">
        <input id="lokalizacja" placeholder="Lokalizacja">
        <button onclick="addItem()">Dodaj</button>

        <h3>Usuń przedmiot</h3>
        <input id="delete_item_id" placeholder="Item ID">
        <button onclick="deleteItem()">Usuń</button>

        <h3>QR kod</h3>
        <input id="qr_item_id" placeholder="Item ID">
        <button onclick="generateQR()">Generuj</button>
        <br>
        <img id="qr_img" width="200">

        <h3>Użytkownicy</h3>
        <button onclick="loadUsers()">Pokaż</button>
        <ul id="users"></ul>

        <h3>Dodaj użytkownika</h3>
        <input id="username" placeholder="Username">
        <input id="password" placeholder="Password">
        <select id="user_role">
            <option value="student">student</option>
            <option value="nauczyciel">nauczyciel</option>
            <option value="administrator">administrator</option>
        </select>
        <button onclick="createUser()">Dodaj</button>

        <h3>Usuń użytkownika</h3>
        <input id="delete_user_id" placeholder="User ID">
        <button onclick="deleteUser()">Usuń</button>
    `;
}

// ------------------ API CALLS ------------------

// Availability
async function loadAvailability() {
    const res = await fetch(`${API_URL}/availability/`);
    const data = await res.json();

    const list = document.getElementById("availability");
    list.innerHTML = "";

    data.forEach(a => {
        const li = document.createElement("li");
        li.innerText = `LoanID:${a.id} | ${a.item_name} | Status:${a.status} | User:${a.user_id}`;
        list.appendChild(li);
    });
}

// Student
async function requestLoan() {
    const item_id = parseInt(document.getElementById("loan_item_id").value);
    const user_id = parseInt(document.getElementById("loan_user_id").value);

    await fetch(`${API_URL}/loans/request/`, {
        method: "POST",
        headers: jsonAuthHeaders(),
        body: JSON.stringify({ item_id, user_id })
    });

    alert("Wniosek wysłany");
}

// Teacher

async function approveLoan() {
    const loan_id = parseInt(document.getElementById("approve_id").value);

    await fetch(`${API_URL}/loans/approve/`, {
        method: "POST",
        headers: jsonAuthHeaders(),
        body: JSON.stringify({ loan_id })
    });

    alert("Zatwierdzono");
}

async function teacherLoan() {
    const item_id = parseInt(document.getElementById("teacher_item_id").value);
    const user_id = parseInt(document.getElementById("teacher_user_id").value);

    await fetch(`${API_URL}/loans/teacher/`, {
        method: "POST",
        headers: jsonAuthHeaders(),
        body: JSON.stringify({ item_id, user_id })
    });

    alert("Wypożyczono");
}

async function returnLoan() {
    const loan_id = parseInt(document.getElementById("return_id").value);

    await fetch(`${API_URL}/loans/return/`, {
        method: "POST",
        headers: jsonAuthHeaders(),
        body: JSON.stringify({ loan_id })
    });

    alert("Zwrócono");
}

// Admin

function generateQR() {
    const item_id = document.getElementById("qr_item_id").value;
    const img = document.getElementById("qr_img");

    img.src = `${API_URL}/items/${item_id}/qr`;
}

async function addItem() {
    const nazwa = document.getElementById("nazwa").value;
    const kategoria = document.getElementById("kategoria").value;
    const lokalizacja = document.getElementById("lokalizacja").value;

    await fetch(`${API_URL}/items/`, {
        method: "POST",
        headers: jsonAuthHeaders(),
        body: JSON.stringify({ nazwa, kategoria, lokalizacja })
    });

    alert("Dodano");
}

async function deleteItem() {
    const id = document.getElementById("delete_item_id").value;

    await fetch(`${API_URL}/items/${id}`, {
        method: "DELETE",
        headers: authHeaders()
    });

    alert("Usunięto");
}

async function loadUsers() {
    const res = await fetch(`${API_URL}/users/`);
    const data = await res.json();

    const list = document.getElementById("users");
    list.innerHTML = "";

    data.forEach(u => {
        const li = document.createElement("li");
        li.innerText = `ID:${u.id} | ${u.username} | ${u.role}`;
        list.appendChild(li);
    });
}

async function createUser() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const role = document.getElementById("user_role").value;

    await fetch(`${API_URL}/users/`, {
        method: "POST",
        headers: jsonAuthHeaders(),
        body: JSON.stringify({ username, password, role })
    });

    alert("Użytkownik dodany");
}

async function deleteUser() {
    const id = document.getElementById("delete_user_id").value;

    await fetch(`${API_URL}/users/${id}`, {
        method: "DELETE",
        headers: authHeaders()
    });

    alert("Usunięto użytkownika");
}

async function loadPendingLoans() {
    const res = await fetch(`${API_URL}/loans/pending/`);
    const data = await res.json();

    const list = document.getElementById("pending");
    list.innerHTML = "";

    data.forEach(l => {
        const li = document.createElement("li");
        li.innerText = `LoanID:${l.id} | Item:${l.item_id} | User:${l.user_id}`;
        list.appendChild(li);
    });
}

// init
renderUI();