// Must run (as a classic, non-module script) before vendor/cesium/Cesium.js
// loads, so Cesium can resolve its own Workers/Assets/ThirdParty/Widgets
// subpaths. Can't be an inline <script> tag -- this app's CSP is
// script-src 'self' with no 'unsafe-inline' -- hence this tiny external file.
window.CESIUM_BASE_URL = "/static/js/vendor/cesium/";
