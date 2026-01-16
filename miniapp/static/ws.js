let WS = null;

function startWebSocket() {
  if (WS) return;

  const proto = location.protocol === "https:" ? "wss://" : "ws://";
  const WS_HOST = location.host;

  console.log("Connecting to WS:", proto + WS_HOST + "/ws");

  WS = new WebSocket(proto + WS_HOST + "/ws");

  WS.onopen = () => console.log("✅ WS connected");

  WS.onmessage = e => {
    const event = JSON.parse(e.data);
    handleWsEvent(event);
  };

  WS.onclose = () => {
    WS = null;
    setTimeout(startWebSocket, 1500);
  };

  WS.onerror = () => WS.close();
}



function handleWsEvent(event) {
  if (event.branch_id !== CURRENT_BRANCH) return;

  switch (event.type) {

    /* ---------- ROOMS / BEDS ---------- */
    case "rooms_changed":
      if (typeof loadRooms === "function") loadRooms();
      break;

    case "beds_changed":
      if (
        typeof CURRENT_ROOM_ID !== "undefined" &&
        event.room_id === CURRENT_ROOM_ID &&
        typeof loadBeds === "function"
      ) {
        loadBeds(CURRENT_ROOM_ID);
      }

      if (typeof loadAvailableBeds === "function") {
        loadAvailableBeds();
      }

      if (typeof loadDashboard === "function") {
        loadDashboard();
      }
      break;

    /* ---------- BOOKINGS ---------- */
    case "booking_changed":
      if (typeof loadActiveBookings === "function") {
        loadActiveBookings();
      }
      if (typeof loadDashboard === "function") {
        loadDashboard();
      }
      break;

    /* ---------- PAYMENTS / DEBTS ---------- */
    case "payments_changed":
      if (typeof loadPaymentHistory === "function") {
        loadPaymentHistory();
      }
      if (typeof loadDebts === "function") {
        loadDebts();
      }
      if (typeof loadDashboard === "function") {
        loadDashboard();
      }
      break;

    /* ---------- CUSTOMERS ---------- */
    case "customers_changed":
      if (typeof loadCustomers === "function") {
        loadCustomers();
      }
      break;
  }
}

