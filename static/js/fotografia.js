(() => {
    const input = document.querySelector('[data-foto-input]');
    if (!input) return;
    const preview = document.querySelector('[data-foto-preview]');
    const image = document.querySelector('[data-foto-imagen]');
    const filename = document.querySelector('[data-foto-nombre]');
    const emptyMessage = filename.dataset.sinSeleccion;
    const error = document.querySelector('[data-foto-error]');
    let objectURL;
    const clear = () => {
        preview.hidden = true;
        image.removeAttribute('src');
        if (objectURL) URL.revokeObjectURL(objectURL);
        objectURL = undefined;
    };
    input.addEventListener('change', () => {
        clear(); error.textContent = '';
        const file = input.files[0];
        filename.textContent = file ? 'Archivo seleccionado: ' + file.name : emptyMessage;
        if (!file) return;
        if (file.size > 2 * 1024 * 1024) {
            error.textContent = 'La fotografía debe pesar como máximo 2 MB.';
            input.value = ''; filename.textContent = emptyMessage; return;
        }
        if (!['image/jpeg', 'image/png'].includes(file.type)) {
            error.textContent = 'Selecciona una fotografía JPG o PNG válida.';
            input.value = ''; filename.textContent = emptyMessage; return;
        }
        image.onload = () => {
            if (image.naturalWidth * image.naturalHeight > 12000000 || Math.max(image.naturalWidth, image.naturalHeight) > 6000) {
                clear(); input.value = ''; filename.textContent = emptyMessage;
                error.textContent = 'La imagen supera el límite de 12 megapíxeles o 6000 píxeles por lado. Reduce sus dimensiones en un editor de imágenes hasta cumplir ambos límites y vuelve a seleccionarla.';
            } else preview.hidden = false;
        };
        image.onerror = () => {
            clear(); input.value = ''; filename.textContent = emptyMessage;
            error.textContent = 'El archivo está dañado o no es una imagen válida.';
        };
        objectURL = URL.createObjectURL(file);
        image.src = objectURL;
    });
    window.addEventListener('pagehide', clear);
})();
