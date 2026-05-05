export function applyArtistTheme(themeColor: string) {
  document.documentElement.style.setProperty("--artist-color", themeColor);
}

export function clearArtistTheme() {
  document.documentElement.style.removeProperty("--artist-color");
}
