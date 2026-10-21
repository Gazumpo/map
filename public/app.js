"use strict";

const PERTH_VIEW = [-31.9523, 115.8613];
const SEARCH_ENDPOINT = "https://nominatim.openstreetmap.org/search";
const SEARCH_CACHE_KEY = "map-search-cache-v1";
const SEARCH_CACHE_TTL = 7 * 24 * 60 * 60 * 1000;
const BASE_MAP_STORAGE_KEY = "map-base-map-v1";
const DATA_ATTRIBUTION =
  'Data: <a href="https://data.gov.au/data/dataset/national-public-toilet-map">National Public Toilet Map</a>, ' +
  '<a href="https://catalogue.data.wa.gov.au/dataset/perth-street-appurtenances">City of Perth</a>, ' +
  '<a href="https://catalogue.data.wa.gov.au/dataset/mrwa-road-network">Main Roads WA PSP network</a>, ' +
  '<a href="https://www.thecrag.com/en/climbing/australia/western-australia/perth">theCrag</a>, ' +
  '<a href="https://www.surf-forecast.com/countries/Australia/breaks">Surf-Forecast</a>, ' +
  '<a href="https://www.mybeach.com.au/">Surf Life Saving WA</a>, ' +
  '<a href="https://waveexplorers.com/guide/australia/perth/surfing-cottesloe/">Wave Explorers</a>, ' +
  '<a href="https://www.wannasurf.com/spot/Australia_Pacific/Australia/WA/Perth_South/tims_thicket/">WannaSurf</a>, ' +
  '<a href="https://exploreparks.dbca.wa.gov.au/activity/snorkelling">DBCA snorkelling guides</a>, ' +
  '<a href="https://www.rottnestisland.com/see-do/beaches-water-activities/Snorkelling-Diving">Rottnest Island Authority</a>, ' +
  '<a href="https://www.cockburn.wa.gov.au/Adventure-and-Leisure/Nature-and-Outdoors/Trails-and-Lookouts/Coogee-Maritime-Trail">Coogee Maritime Trail</a>, ' +
  '<a href="https://www.openstreetmap.org/copyright">OpenStreetMap amenities</a>';

const map = L.map("map", {
  zoomControl: false,
  preferCanvas: true,
  zoomSnap: 0.5,
  minZoom: 8,
}).setView(PERTH_VIEW, 10);

// Safari does not always send the click events Leaflet uses for double taps.
enableMapDoubleTap(map);

// Refresh tiles when the viewport changes on rotation or browser-bar changes.
const mapResizeObserver = new ResizeObserver(() => {
  map.invalidateSize({ pan: false });
});
mapResizeObserver.observe(map.getContainer());

L.control.zoom({ position: "bottomright" }).addTo(map);

function enableMapDoubleTap(map) {
  const container = map.getContainer();
  const controls = ".leaflet-control, .leaflet-popup, .leaflet-tooltip, button, input, select, textarea, a";
  let start = null;
  let lastTap = null;
  let ignoreDoubleClickUntil = 0;
  const nearby = (a, b) => Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY) <= 25;
  const reset = () => {
    start = null;
    lastTap = null;
  };

  container.addEventListener("touchstart", (event) => {
    if (event.touches.length !== 1 || event.target.closest(controls)) {
      reset();
      return;
    }
    const touch = event.touches[0];
    start = { clientX: touch.clientX, clientY: touch.clientY, time: event.timeStamp };
  }, { passive: true });

  container.addEventListener("touchmove", (event) => {
    if (event.touches.length !== 1 || (start && !nearby(start, event.touches[0]))) reset();
  }, { passive: true });
  container.addEventListener("touchcancel", reset, { passive: true });

  container.addEventListener("touchend", (event) => {
    const touch = event.changedTouches[0];
    if (!start || event.touches.length || !touch || !nearby(start, touch)
      || event.timeStamp - start.time > 250 || !map.doubleClickZoom.enabled()) {
      reset();
      return;
    }
    start = null;
    const tap = { clientX: touch.clientX, clientY: touch.clientY, time: event.timeStamp };
    if (lastTap && tap.time - lastTap.time <= 300 && nearby(lastTap, tap)) {
      // Cancel the second click so Leaflet cannot zoom a second time.
      event.preventDefault();
      ignoreDoubleClickUntil = tap.time + 400;
      lastTap = null;
      const zoom = map.getZoom() + map.options.zoomDelta;
      if (map.options.doubleClickZoom === "center") map.setZoom(zoom);
      else map.setZoomAround(map.mouseEventToContainerPoint(touch), zoom);
    } else {
      lastTap = tap;
    }
  }, { passive: false });

  container.addEventListener("dblclick", (event) => {
    if (event.timeStamp < ignoreDoubleClickUntil) event.stopImmediatePropagation();
  }, { capture: true });
}

const baseMaps = {
  map: L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> | ' +
      DATA_ATTRIBUTION,
    maxZoom: 19,
  }),
  satellite: L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      attribution:
        'Tiles &copy; <a href="https://www.esri.com/">Esri</a>, Maxar, Earthstar Geographics, and the GIS User Community | ' +
        DATA_ATTRIBUTION,
      maxZoom: 19,
    },
  ),
  terrain: L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    {
      attribution:
        'Tiles &copy; <a href="https://www.esri.com/">Esri</a> and contributors | ' +
        DATA_ATTRIBUTION,
      maxZoom: 19,
    },
  ),
};

function readStoredBaseMap() {
  try {
    const storedType = localStorage.getItem(BASE_MAP_STORAGE_KEY);
    return Object.hasOwn(baseMaps, storedType) ? storedType : "map";
  } catch {
    return "map";
  }
}

const initialBaseMapType = readStoredBaseMap();
baseMaps[initialBaseMapType].addTo(map);

map.createPane("mapPoints");
map.getPane("mapPoints").style.zIndex = 430;
map.createPane("userLocation");
map.getPane("userLocation").style.zIndex = 650;

const elements = {
  map: document.querySelector("#map"),
  itemPanel: document.querySelector(".map-toolbar"),
  mapTypeControl: document.querySelector("#map-type-control"),
  mapTypeToggle: document.querySelector("#map-type-toggle"),
  mapTypeOptions: document.querySelector("#map-type-options"),
  mapTypeButtons: document.querySelectorAll("[data-map-type]"),
  waterToggle: document.querySelector("#water-toggle"),
  toiletToggle: document.querySelector("#toilet-toggle"),
  moreLayersToggle: document.querySelector("#more-layers-toggle"),
  extraLayerToggles: document.querySelector("#extra-layer-toggles"),
  selectedLayerSummary: document.querySelector("#selected-layer-summary"),
  pspToggle: document.querySelector("#psp-toggle"),
  showerToggle: document.querySelector("#shower-toggle"),
  adultChangeToggle: document.querySelector("#adult-change-toggle"),
  babyChangeToggle: document.querySelector("#baby-change-toggle"),
  bbqToggle: document.querySelector("#bbq-toggle"),
  boulderingToggle: document.querySelector("#bouldering-toggle"),
  climbingToggle: document.querySelector("#climbing-toggle"),
  surfToggle: document.querySelector("#surf-toggle"),
  snorkellingToggle: document.querySelector("#snorkelling-toggle"),
  waterCount: document.querySelector("#water-count"),
  toiletCount: document.querySelector("#toilet-count"),
  showerCount: document.querySelector("#shower-count"),
  adultChangeCount: document.querySelector("#adult-change-count"),
  babyChangeCount: document.querySelector("#baby-change-count"),
  bbqCount: document.querySelector("#bbq-count"),
  boulderingCount: document.querySelector("#bouldering-count"),
  climbingCount: document.querySelector("#climbing-count"),
  surfCount: document.querySelector("#surf-count"),
  snorkellingCount: document.querySelector("#snorkelling-count"),
  pspCount: document.querySelector("#psp-count"),
  searchForm: document.querySelector("#search-form"),
  searchInput: document.querySelector("#search-input"),
  searchButton: document.querySelector("#search-button"),
  searchResults: document.querySelector("#search-results"),
  searchMessage: document.querySelector("#search-message"),
  searchList: document.querySelector("#search-list"),
  locateButton: document.querySelector("#locate-button"),
  locateLabel: document.querySelector("#locate-label"),
  statusMessage: document.querySelector("#status-message"),
};

const state = {
  waterLayer: null,
  toiletLayer: null,
  showerLayer: null,
  adultChangeLayer: null,
  babyChangeLayer: null,
  bbqLayer: null,
  boulderingLayer: null,
  climbingLayer: null,
  surfLayer: null,
  snorkellingLayer: null,
  pspLayer: null,
  activeBaseMapType: initialBaseMapType,
  waterVisible: false,
  toiletsVisible: false,
  showersVisible: false,
  adultChangeVisible: false,
  babyChangeVisible: false,
  bbqsVisible: false,
  boulderingVisible: false,
  climbingVisible: false,
  surfVisible: false,
  snorkellingVisible: false,
  pspVisible: false,
  userLatLng: null,
  userMarker: null,
  accuracyCircle: null,
  searchMarker: null,
  statusTimer: null,
  lastSearchAt: 0,
};

// Point-address match from Esri's geocoding service, verified 14 October 2026.
const houseLatLng = L.latLng(-31.983259991735, 115.77622004588);
L.marker(houseLatLng, {
  icon: L.icon({
    iconUrl: "/map/house.svg",
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    popupAnchor: [0, -9],
    tooltipAnchor: [0, -9],
  }),
  title: "28 Mount Street, Claremont",
  alt: "House at 28 Mount Street, Claremont",
  riseOnHover: true,
})
  .bindTooltip("28 Mount Street, Claremont", { direction: "top" })
  .bindPopup(() => makePopup({
    properties: { name: "28 Mount Street", address: "Claremont, WA 6010" },
  }, houseLatLng))
  .addTo(map);

function setBaseMap(type) {
  if (!Object.hasOwn(baseMaps, type)) return;

  if (type !== state.activeBaseMapType) {
    map.removeLayer(baseMaps[state.activeBaseMapType]);
    baseMaps[type].addTo(map);
    state.activeBaseMapType = type;
  }

  for (const button of elements.mapTypeButtons) {
    const active = button.dataset.mapType === type;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
    if (active) {
      elements.mapTypeToggle.setAttribute("aria-label", `Map layers, current view: ${button.textContent}`);
    }
  }

  try {
    localStorage.setItem(BASE_MAP_STORAGE_KEY, type);
  } catch {
    // Map switching still works when storage is unavailable.
  }
}

setBaseMap(initialBaseMapType);
updateSelectedLayerSummary();

function closeMapTypeOptions(restoreFocus = false) {
  elements.mapTypeOptions.hidden = true;
  elements.mapTypeToggle.setAttribute("aria-expanded", "false");
  if (restoreFocus) elements.mapTypeToggle.focus();
}

function toggleMapTypeOptions() {
  if (!elements.mapTypeOptions.hidden) {
    closeMapTypeOptions();
    return;
  }
  elements.mapTypeOptions.hidden = false;
  elements.mapTypeToggle.setAttribute("aria-expanded", "true");
  elements.mapTypeOptions.querySelector('[aria-pressed="true"]').focus();
}

function showStatus(message, timeout = 4500) {
  window.clearTimeout(state.statusTimer);
  elements.statusMessage.textContent = message;
  elements.statusMessage.hidden = false;
  state.statusTimer = window.setTimeout(() => {
    elements.statusMessage.hidden = true;
  }, timeout);
}

function formatDistance(metres) {
  if (metres < 1000) {
    return `${Math.max(10, Math.round(metres / 10) * 10)} m away`;
  }
  return `${(metres / 1000).toFixed(metres < 10000 ? 1 : 0)} km away`;
}

function appendPopupDetail(popup, label, value) {
  if (!value) return;
  const detail = document.createElement("p");
  detail.className = "point-detail";
  const heading = document.createElement("strong");
  heading.textContent = `${label}: `;
  detail.append(heading, document.createTextNode(value));
  popup.append(detail);
}

function amenitySummary(properties) {
  const amenities = [];
  if (properties.accessible) amenities.push("accessible toilet");
  if (properties.ambulant) amenities.push("ambulant toilet");
  if (properties.changingPlaces) amenities.push("Changing Places");
  else if (properties.adultChange) amenities.push("adult change table");
  if (properties.babyChange) amenities.push("baby change");
  if (properties.drinkingWater) amenities.push("drinking water");
  if (properties.bottleFilling) amenities.push("bottle filling");
  if (properties.dogBowl) amenities.push("dog bowl");
  if (properties.shower) amenities.push("shower");
  if (properties.sharpsDisposal) amenities.push("sharps disposal");
  if (properties.category === "bbq") {
    amenities.push(properties.kind === "double" ? "double-plate BBQ" : "public BBQ");
  }
  return amenities.join(", ");
}

function makePopup(feature, latlng, compact = false) {
  const properties = feature.properties;
  const popup = document.createElement("article");
  popup.className = "point-popup";

  const heading = document.createElement("h2");
  heading.textContent = properties.name;
  popup.append(heading);

  if (properties.description) {
    const notes = document.createElement("p");
    notes.textContent = properties.description;
    popup.append(notes);
  }

  appendPopupDetail(popup, "Address", properties.address);
  appendPopupDetail(popup, "Location", properties.addressNote);
  appendPopupDetail(popup, "Hours", properties.openingHours);
  appendPopupDetail(popup, "Hours note", properties.openingHoursNote);
  appendPopupDetail(popup, "Facilities", amenitySummary(properties));
  appendPopupDetail(popup, "Access", properties.accessNote);

  if (properties.category === "climbing") {
    appendPopupDetail(popup, "Routes", String(properties.routeCount));
    appendPopupDetail(popup, "Primary type", properties.primaryType);
  }

  if (properties.category === "surf") {
    appendPopupDetail(popup, "Type of surf", properties.surfType);
    appendPopupDetail(popup, "Season", properties.season);
  }

  if (properties.category === "snorkelling") {
    appendPopupDetail(popup, "Area", properties.area);
    appendPopupDetail(popup, "Season", properties.season);
    appendPopupDetail(popup, "Conditions", properties.conditions);
  }

  const entryRequirements = [];
  if (properties.paymentRequired) entryRequirements.push("payment required");
  if (properties.keyRequired) entryRequirements.push("key required");
  if (properties.mlak24) entryRequirements.push("MLAK access 24 hours");
  else if (properties.mlakAfterHours) entryRequirements.push("MLAK access after hours");
  appendPopupDetail(popup, "Entry", entryRequirements.join(", "));

  if (!compact) {
    const distance = document.createElement("p");
    distance.className = "point-distance";
    distance.textContent = state.userLatLng
      ? formatDistance(map.distance(state.userLatLng, latlng))
      : "Use Locate me to see the distance";
    popup.append(distance);

    const directions = document.createElement("a");
    directions.className = "directions-link";
    directions.href = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(
      `${latlng.lat},${latlng.lng}`,
    )}&travelmode=walking`;
    directions.target = "_blank";
    directions.rel = "noopener noreferrer";
    directions.textContent = "Directions in Google Maps";
    popup.append(directions);
  }

  const sourceUrl =
    properties.theCragUrl || properties.facilityUrl || properties.sourceUrl;
  if (sourceUrl) {
    const source = document.createElement("a");
    source.className = "source-link";
    source.href = sourceUrl;
    source.target = "_blank";
    source.rel = "noopener noreferrer";
    if (properties.category === "surf") {
      source.textContent = "Surf guide and area information";
    } else if (properties.category === "snorkelling") {
      source.textContent = "Snorkelling guide and area information";
    } else if (properties.theCragUrl) {
      source.textContent = "View on theCrag";
    } else if (properties.facilityUrl) {
      source.textContent = "View official facility listing";
    } else {
      source.textContent = "View data source";
    }
    popup.append(source);
  }

  return popup;
}

function pointStyle(category) {
  const colours = {
    water: "#1478e8",
    toilet: "#dc2626",
    shower: "#0891b2",
    "adult-change": "#7c3aed",
    "baby-change": "#db2777",
    bbq: "#c2410c",
    bouldering: "#eab308",
    climbing: "#334155",
    surf: "#0f766e",
    snorkelling: "#4f46e5",
  };
  return {
    pane: "mapPoints",
    radius: 6,
    color: "#ffffff",
    weight: 2,
    fillColor: colours[category],
    fillOpacity: 0.94,
  };
}

function makePointLayer(data, category) {
  return L.geoJSON(data, {
    pointToLayer(feature, latlng) {
      const marker = L.circleMarker(latlng, pointStyle(category));
      marker.bindPopup(() => makePopup(feature, latlng), {
        maxWidth: 290,
        minWidth: 210,
        ...(category === "snorkelling" ? {
          maxHeight: 360,
          autoPanPaddingTopLeft: [20, 150],
          autoPanPaddingBottomRight: [20, 45],
        } : {}),
      });
      if (category === "snorkelling") {
        bindSnorkellingHover(marker, feature, latlng);
      }
      return marker;
    },
  });
}

function bindSnorkellingHover(marker, feature, latlng) {
  const tooltip = L.tooltip({
    interactive: true,
    direction: "auto",
    opacity: 1,
    className: "snorkelling-tooltip",
  }).setLatLng(latlng).setContent(makePopup(feature, latlng, true));
  let closeTimer;
  const cancelClose = () => window.clearTimeout(closeTimer);
  const close = () => {
    cancelClose();
    tooltip.remove();
  };
  // Give the pointer time to cross the gap from a canvas marker to its guide link.
  const scheduleClose = () => {
    cancelClose();
    closeTimer = window.setTimeout(close, 250);
  };
  tooltip.on("add", () => {
    const container = tooltip.getElement();
    container.addEventListener("mouseenter", cancelClose);
    container.addEventListener("mouseleave", scheduleClose);
    const bounds = map.getContainer().getBoundingClientRect();
    const card = container.getBoundingClientRect();
    const dx = Math.max(bounds.left + 10 - card.left, 0)
      + Math.min(bounds.right - 10 - card.right, 0);
    const dy = Math.max(bounds.top + 150 - card.top, 0)
      + Math.min(bounds.bottom - 75 - card.bottom, 0);
    tooltip.options.offset = [dx, dy];
    tooltip.update();
  });
  marker.on("mouseover", () => {
    cancelClose();
    if (!marker.isPopupOpen() && !map.hasLayer(tooltip)) {
      tooltip.options.offset = [0, 0];
      tooltip.addTo(map);
    }
  });
  marker.on("mouseout", scheduleClose);
  marker.on("click popupopen remove", close);
}

function makePspPopup(feature) {
  const properties = feature.properties;
  const popup = document.createElement("article");
  popup.className = "point-popup";

  const heading = document.createElement("h2");
  heading.textContent = properties.name;
  popup.append(heading);

  appendPopupDetail(popup, "Route", properties.routeCode);
  appendPopupDetail(popup, "Local government", properties.council);
  if (properties.isStairs) {
    appendPopupDetail(popup, "Access", "Stairs - not a rideable path segment");
  } else if (properties.isConnector) {
    appendPopupDetail(popup, "Access", "PSP connection");
  }

  const source = document.createElement("a");
  source.className = "source-link";
  source.href = properties.sourceUrl;
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  source.textContent = "View Main Roads data source";
  popup.append(source);

  return popup;
}

function pspStyle(feature) {
  const properties = feature.properties;
  return {
    pane: "mapPoints",
    color: properties.isStairs ? "#64748b" : "#15803d",
    weight: properties.isConnector ? 3 : 5,
    opacity: properties.isConnector ? 0.78 : 0.9,
    dashArray: properties.isStairs ? "4 5" : null,
    lineCap: "round",
    lineJoin: "round",
  };
}

function makePspLayer(data) {
  return L.geoJSON(data, {
    style: pspStyle,
    onEachFeature(feature, layer) {
      layer.bindPopup(() => makePspPopup(feature), {
        maxWidth: 290,
        minWidth: 210,
      });
    },
  });
}

function countPspRoutes(data) {
  return new Set(
    data.features.map((feature) => feature.properties.parentRouteCode),
  ).size;
}

function updateSelectedLayerSummary() {
  const selected = Array.from(
    elements.extraLayerToggles.querySelectorAll('[aria-pressed="true"]'),
    (button) => ({ label: button.dataset.layerLabel, colour: button.dataset.layerColour }),
  );
  const summary = selected.length ? selected.map((item) => item.label).join(", ") : "No items selected";
  elements.selectedLayerSummary.replaceChildren();
  if (!selected.length) elements.selectedLayerSummary.textContent = summary;
  selected.forEach((item, index) => {
    if (index) elements.selectedLayerSummary.append(document.createTextNode(", "));
    const name = document.createElement("span");
    name.className = "selected-layer-name";
    name.dataset.layerColour = item.colour;
    name.textContent = item.label;
    elements.selectedLayerSummary.append(name);
  });
  const expanded = elements.moreLayersToggle.getAttribute("aria-expanded") === "true";
  elements.moreLayersToggle.setAttribute(
    "aria-label",
    `${expanded ? "Hide" : "Choose"} map items. Showing: ${summary}`,
  );
}

function setToggleState(button, active) {
  button.classList.toggle("is-active", active);
  button.setAttribute("aria-pressed", String(active));
  updateSelectedLayerSummary();
}

function toggleLayer(category) {
  const settings = {
    water: ["waterLayer", "waterVisible", elements.waterToggle, "Water points"],
    toilet: ["toiletLayer", "toiletsVisible", elements.toiletToggle, "Toilets"],
    shower: ["showerLayer", "showersVisible", elements.showerToggle, "Showers"],
    "adult-change": [
      "adultChangeLayer",
      "adultChangeVisible",
      elements.adultChangeToggle,
      "Adult change facilities",
    ],
    "baby-change": [
      "babyChangeLayer",
      "babyChangeVisible",
      elements.babyChangeToggle,
      "Baby change facilities",
    ],
    bbq: ["bbqLayer", "bbqsVisible", elements.bbqToggle, "Public BBQs"],
    bouldering: [
      "boulderingLayer",
      "boulderingVisible",
      elements.boulderingToggle,
      "Bouldering locations",
    ],
    climbing: [
      "climbingLayer",
      "climbingVisible",
      elements.climbingToggle,
      "Climbing locations",
    ],
    psp: ["pspLayer", "pspVisible", elements.pspToggle, "PSP routes"],
    surf: ["surfLayer", "surfVisible", elements.surfToggle, "Surf spots"],
    snorkelling: [
      "snorkellingLayer",
      "snorkellingVisible",
      elements.snorkellingToggle,
      "Snorkelling spots",
    ],
  };
  const [layerKey, visibleKey, toggle, label] = settings[category];
  const layer = state[layerKey];
  if (!layer) {
    showStatus(`${label} could not be loaded. Please try again later.`, 6500);
    return;
  }

  const currentlyVisible = state[visibleKey];
  if (currentlyVisible) {
    map.removeLayer(layer);
  } else {
    layer.addTo(map);
    if (category === "psp") layer.bringToBack();
  }
  state[visibleKey] = !currentlyVisible;
  setToggleState(toggle, state[visibleKey]);
}

function fitInitialView() {
  const bounds = state.waterLayer?.getBounds();
  if (!bounds?.isValid()) return;
  map.fitBounds(bounds, {
    paddingTopLeft: [20, 150],
    paddingBottomRight: [20, 45],
    maxZoom: 11,
  });
}

async function loadPoints() {
  const definitions = [
    [
      "snorkelling",
      "snorkelling-spots.geojson",
      "snorkellingLayer",
      elements.snorkellingToggle,
      elements.snorkellingCount,
      false,
    ],
    [
      "surf",
      "surf-spots.geojson",
      "surfLayer",
      elements.surfToggle,
      elements.surfCount,
      false,
    ],
    [
      "water",
      "water-points.geojson",
      "waterLayer",
      elements.waterToggle,
      elements.waterCount,
      false,
    ],
    [
      "toilet",
      "toilets.geojson",
      "toiletLayer",
      elements.toiletToggle,
      elements.toiletCount,
      false,
    ],
    [
      "shower",
      "showers.geojson",
      "showerLayer",
      elements.showerToggle,
      elements.showerCount,
      false,
    ],
    [
      "adult-change",
      "adult-change.geojson",
      "adultChangeLayer",
      elements.adultChangeToggle,
      elements.adultChangeCount,
      false,
    ],
    [
      "baby-change",
      "baby-change.geojson",
      "babyChangeLayer",
      elements.babyChangeToggle,
      elements.babyChangeCount,
      false,
    ],
    [
      "bbq",
      "bbqs.geojson",
      "bbqLayer",
      elements.bbqToggle,
      elements.bbqCount,
      false,
    ],
    [
      "bouldering",
      "climbing-locations.geojson",
      "boulderingLayer",
      elements.boulderingToggle,
      elements.boulderingCount,
      false,
      "bouldering",
    ],
    [
      "climbing",
      "climbing-locations.geojson",
      "climbingLayer",
      elements.climbingToggle,
      elements.climbingCount,
      false,
      "climbing",
    ],
    [
      "psp",
      "psp-routes.geojson",
      "pspLayer",
      elements.pspToggle,
      elements.pspCount,
      false,
    ],
  ];
  let failedCount = 0;
  const loads = definitions.map(
    async ([category, filename, layerKey, toggle, count, visible, climbingKind]) => {
      try {
        const response = await fetch(`/map/data/${filename}`);
        if (!response.ok) throw new Error(`${filename} could not be loaded`);
        const data = await response.json();
        const layerData = climbingKind
          ? {
              ...data,
              features: data.features.filter(
                (feature) => feature.properties.climbingKind === climbingKind,
              ),
            }
          : data;
        state[layerKey] = category === "psp"
          ? makePspLayer(data)
          : makePointLayer(layerData, category);
        if (visible) state[layerKey].addTo(map);
        count.textContent = category === "psp"
          ? countPspRoutes(data)
          : layerData.features.length;
        toggle.disabled = false;
      } catch {
        failedCount += 1;
        toggle.disabled = false;
        toggle.classList.add("has-load-error");
        toggle.setAttribute("aria-label", `${toggle.textContent.trim()} unavailable`);
        setToggleState(toggle, false);
        if (category === "water") {
          state.waterVisible = false;
        }
      }
    },
  );

  await Promise.all(loads);
  if (state.waterLayer) fitInitialView();
  if (failedCount) {
    showStatus(
      `${failedCount} map layer${failedCount === 1 ? "" : "s"} could not be loaded.`,
      7000,
    );
  }

  elements.map.setAttribute("aria-busy", "false");
}

function setItemPanelExpanded(expanded, restoreFocus = false) {
  elements.moreLayersToggle.setAttribute("aria-expanded", String(expanded));
  elements.extraLayerToggles.hidden = !expanded;
  updateSelectedLayerSummary();
  if (restoreFocus) elements.moreLayersToggle.focus();
}

function toggleMoreLayers() {
  setItemPanelExpanded(elements.extraLayerToggles.hidden);
}

function clearLocationLayers() {
  if (state.userMarker) map.removeLayer(state.userMarker);
  if (state.accuracyCircle) map.removeLayer(state.accuracyCircle);
}

function showUserLocation(position) {
  const { latitude, longitude, accuracy } = position.coords;
  state.userLatLng = L.latLng(latitude, longitude);
  clearLocationLayers();

  state.accuracyCircle = L.circle(state.userLatLng, {
    pane: "userLocation",
    radius: accuracy,
    color: "#111827",
    weight: 1,
    fillColor: "#111827",
    fillOpacity: 0.12,
    interactive: false,
  }).addTo(map);

  state.userMarker = L.circleMarker(state.userLatLng, {
    pane: "userLocation",
    radius: 8,
    color: "#ffffff",
    weight: 3,
    fillColor: "#111827",
    fillOpacity: 1,
  })
    .bindTooltip("Your location", { direction: "top", offset: [0, -7] })
    .addTo(map);

  map.setView(state.userLatLng, Math.max(map.getZoom(), 15));
  elements.locateButton.disabled = false;
  elements.locateLabel.textContent = "Recenter";
  showStatus(`Location found, accurate to about ${Math.round(accuracy)} m.`);
}

function locationFailed(error) {
  elements.locateButton.disabled = false;
  elements.locateLabel.textContent = "Locate me";
  if (error.code === error.PERMISSION_DENIED) {
    showStatus("Location permission was declined. You can still browse and search the map.", 6500);
    return;
  }
  showStatus("Your location could not be found. Please try again.", 6500);
}

function locateUser() {
  if (!navigator.geolocation) {
    showStatus("Location is not available in this browser.", 6500);
    return;
  }

  if (state.userLatLng) {
    map.setView(state.userLatLng, Math.max(map.getZoom(), 15));
    return;
  }

  elements.locateButton.disabled = true;
  elements.locateLabel.textContent = "Locating...";
  navigator.geolocation.getCurrentPosition(showUserLocation, locationFailed, {
    enableHighAccuracy: true,
    timeout: 12000,
    maximumAge: 60000,
  });
}

function getSearchCache() {
  try {
    return JSON.parse(localStorage.getItem(SEARCH_CACHE_KEY) || "{}");
  } catch {
    return {};
  }
}

function readCachedSearch(query) {
  const entry = getSearchCache()[query];
  if (!entry || Date.now() - entry.savedAt > SEARCH_CACHE_TTL) return null;
  return entry.results;
}

function cacheSearch(query, results) {
  try {
    const cache = getSearchCache();
    cache[query] = { savedAt: Date.now(), results };
    localStorage.setItem(SEARCH_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // Searching still works when storage is unavailable.
  }
}

function selectSearchResult(result) {
  const lat = Number(result.lat);
  const lon = Number(result.lon);
  const latlng = L.latLng(lat, lon);

  if (state.searchMarker) map.removeLayer(state.searchMarker);
  state.searchMarker = L.circleMarker(latlng, {
    radius: 7,
    color: "#172033",
    weight: 2,
    fillColor: "#ffffff",
    fillOpacity: 1,
  }).addTo(map);

  if (Array.isArray(result.boundingbox) && result.boundingbox.length === 4) {
    const [south, north, west, east] = result.boundingbox.map(Number);
    map.fitBounds(
      [
        [south, west],
        [north, east],
      ],
      { padding: [35, 35], maxZoom: 16 },
    );
  } else {
    map.setView(latlng, 15);
  }

  state.searchMarker.bindTooltip(result.display_name, {
    permanent: false,
    direction: "top",
  });
  elements.searchResults.hidden = true;
  elements.searchInput.blur();
}

function renderSearchResults(results) {
  elements.searchList.replaceChildren();
  elements.searchResults.hidden = false;

  if (!results.length) {
    elements.searchMessage.textContent = "No matching places found. Try a suburb or a more specific address.";
    return;
  }

  elements.searchMessage.textContent = `${results.length} result${results.length === 1 ? "" : "s"} from OpenStreetMap`;
  for (const result of results) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.className = "search-result";
    button.type = "button";
    button.textContent = result.display_name;
    button.addEventListener("click", () => selectSearchResult(result));
    item.append(button);
    elements.searchList.append(item);
  }
}

function waitForSearchWindow() {
  const remaining = 1000 - (Date.now() - state.lastSearchAt);
  return remaining > 0
    ? new Promise((resolve) => window.setTimeout(resolve, remaining))
    : Promise.resolve();
}

async function searchPlaces(event) {
  event.preventDefault();
  const query = elements.searchInput.value.trim().replace(/\s+/g, " ");
  if (query.length < 2) {
    elements.searchResults.hidden = false;
    elements.searchMessage.textContent = "Enter a suburb or address to search.";
    elements.searchList.replaceChildren();
    return;
  }

  const cacheKey = query.toLocaleLowerCase("en-AU");
  const cached = readCachedSearch(cacheKey);
  if (cached) {
    renderSearchResults(cached);
    return;
  }

  elements.searchButton.disabled = true;
  elements.searchButton.textContent = "Searching...";
  elements.searchResults.hidden = false;
  elements.searchMessage.textContent = "Searching...";
  elements.searchList.replaceChildren();

  try {
    await waitForSearchWindow();
    state.lastSearchAt = Date.now();
    const params = new URLSearchParams({
      q: `${query}, Western Australia`,
      format: "jsonv2",
      addressdetails: "0",
      limit: "5",
      countrycodes: "au",
      viewbox: "114.5,-30.8,116.5,-33.2",
      bounded: "0",
      "accept-language": "en-AU",
    });
    const response = await fetch(`${SEARCH_ENDPOINT}?${params}`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error("Search failed");
    const results = await response.json();
    cacheSearch(cacheKey, results);
    renderSearchResults(results);
  } catch {
    elements.searchMessage.textContent = "Search is unavailable right now. Please try again shortly.";
  } finally {
    elements.searchButton.disabled = false;
    elements.searchButton.textContent = "Search";
  }
}

elements.waterToggle.addEventListener("click", () => toggleLayer("water"));
elements.toiletToggle.addEventListener("click", () => toggleLayer("toilet"));
elements.moreLayersToggle.addEventListener("click", toggleMoreLayers);
elements.itemPanel.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !elements.extraLayerToggles.hidden) {
    event.preventDefault();
    setItemPanelExpanded(false, true);
  }
});
elements.pspToggle.addEventListener("click", () => toggleLayer("psp"));
elements.showerToggle.addEventListener("click", () => toggleLayer("shower"));
elements.adultChangeToggle.addEventListener("click", () => toggleLayer("adult-change"));
elements.babyChangeToggle.addEventListener("click", () => toggleLayer("baby-change"));
elements.bbqToggle.addEventListener("click", () => toggleLayer("bbq"));
elements.boulderingToggle.addEventListener("click", () => toggleLayer("bouldering"));
elements.climbingToggle.addEventListener("click", () => toggleLayer("climbing"));
elements.surfToggle.addEventListener("click", () => toggleLayer("surf"));
elements.snorkellingToggle.addEventListener("click", () => toggleLayer("snorkelling"));
for (const button of elements.mapTypeButtons) {
  button.addEventListener("click", () => {
    setBaseMap(button.dataset.mapType);
    closeMapTypeOptions(true);
  });
}
elements.mapTypeToggle.addEventListener("click", toggleMapTypeOptions);
elements.mapTypeControl.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !elements.mapTypeOptions.hidden) {
    event.preventDefault();
    closeMapTypeOptions(true);
  }
});
elements.mapTypeControl.addEventListener("focusout", (event) => {
  if (!elements.mapTypeControl.contains(event.relatedTarget)) closeMapTypeOptions();
});
document.addEventListener("pointerdown", (event) => {
  if (!elements.mapTypeControl.contains(event.target)) closeMapTypeOptions();
  if (!elements.itemPanel.contains(event.target) && !elements.extraLayerToggles.hidden) {
    setItemPanelExpanded(false);
  }
});
elements.locateButton.addEventListener("click", locateUser);
elements.searchForm.addEventListener("submit", searchPlaces);
map.on("click", () => {
  elements.searchResults.hidden = true;
});

loadPoints().catch(() => {
  elements.map.setAttribute("aria-busy", "false");
  showStatus("Map points could not be loaded. Please try again later.", 7000);
});
