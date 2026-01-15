const burger = document.getElementById("burger");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");

burger.onclick = () => {
  sidebar.classList.add("open");
  overlay.classList.add("show");
};

overlay.onclick = closeSidebar;

function closeSidebar() {
  sidebar.classList.remove("open");
  overlay.classList.remove("show");
}

/* Telegram swipe close */
if (window.Telegram?.WebApp) {
  Telegram.WebApp.onEvent("viewportChanged", closeSidebar);
}
