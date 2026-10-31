document.addEventListener("DOMContentLoaded", () => {
    // Inizializzazione all'apertura della pagina
    onLoadPage();
});

/**
 * Funzione di inizializzazione per il caricamento della pagina
 */
async function onLoadPage() {
    try {
        // Notifica di test all'avvio della pagina
      // mostraToast(window.lang(LANG_KEY.PAGE_LOADES_SUCCESS), "success");
    } catch (error) {
        console.error("Errore durante il caricamento della pagina:", error);
    }
}