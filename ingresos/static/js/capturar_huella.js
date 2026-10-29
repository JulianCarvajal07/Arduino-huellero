document.addEventListener('DOMContentLoaded', () => {
    const fpBox   = document.getElementById('fingerprintBox');
    if (!fpBox) return;   // la página no tiene el campo de huella

    const fpTitle = document.getElementById('huellaTitle');
    const fpMsg   = document.getElementById('huellaStatus');
    const fpBtn   = document.getElementById('btnCapturarHuella');
    const fpRetry = document.getElementById('btnReintentarHuella');
    const fpInput = document.getElementById('id_huella_id');
    const csrf    = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const url     = fpBox.dataset.url;

    const TITLES = {
        idle: 'Haz clic en el ícono',
        scanning: 'Escaneando…',
        success: 'Huella capturada',
        error: 'No se pudo capturar',
    };
    const IDLE_MSG = 'luego coloca el dedo sobre el sensor';

    function setHuellaState(state, msg) {
        fpBox.dataset.state = state;
        fpTitle.textContent = TITLES[state];
        if (msg) fpMsg.textContent = msg;
        fpBtn.disabled = (state === 'scanning' || state === 'success');
        fpRetry.hidden = !(state === 'error' || state === 'success');
    }

    // Si el formulario volvió con errores y ya había huella, mostrarla como capturada
    if (fpInput.value) setHuellaState('success', 'Huella registrada correctamente');

    fpBtn.addEventListener('click', async () => {
        setHuellaState('scanning', 'Coloca el dedo sobre el sensor');
        try {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrf },
            });
            const data = await resp.json();
            if (data.ok) {
                fpInput.value = data.huella_id;
                setHuellaState('success', 'Huella registrada correctamente');
            } else {
                setHuellaState('error', data.error + '. Haz clic en el ícono para intentar de nuevo');
            }
        } catch {
            setHuellaState('error', 'Error de conexión con el servidor');
        }
    });

    fpRetry.addEventListener('click', () => {
        fpInput.value = '';
        setHuellaState('idle', IDLE_MSG);
    });
});