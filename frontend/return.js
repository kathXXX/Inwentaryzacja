const API_URL = "";

const params = new URLSearchParams(window.location.search);
const itemId = params.get("item_id");

const title = document.getElementById("title");
const button = document.getElementById("returnBtn");
const message = document.getElementById("message");

async function loadItem() {
    const res = await fetch(`${API_URL}/items/${itemId}`);

    if (!res.ok) {
        title.innerText = "Nie znaleziono przedmiotu";
        return;
    }

    const item = await res.json();

    title.innerText = `Czy chcesz zwrócić: ${item.nazwa}?`;
    button.style.display = "block";
}

button.addEventListener("click", async () => {
    const token = localStorage.getItem("token");

    if (!token) {
        message.innerText = "Musisz być zalogowany jako nauczyciel lub administrator.";
        return;
    }

    const availabilityRes = await fetch(`${API_URL}/availability/details/`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const loans = await availabilityRes.json();
    const loan = loans.find(l => l.item_id == itemId);

    if (!loan) {
        message.innerText = "Nie znaleziono wypożyczenia.";
        return;
    }

    const res = await fetch(`${API_URL}/loans/return/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            loan_id: loan.id
        })
    });

    if (!res.ok) {
        const err = await res.json();
        message.innerText = err.detail || "Nie udało się zwrócić przedmiotu.";
        return;
    }

    message.innerText = "Przedmiot został zwrócony.";
});

loadItem();