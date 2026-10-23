# Prueba local por Wi-Fi

La Mac usa Wi-Fi en0, IP 192.168.1.20 al configurar esta prueba.
Desde un teléfono en la misma red: http://192.168.1.20:8000/.
Acceso: /acceso/, con las cuentas ficticias ya existentes y su contraseña local.

`iniciar-local.sh` acepta RUNSERVER_ADDR; el valor local en `.local/demo.env`
es 0.0.0.0:8000 para escuchar en interfaces IPv4. Sin esa variable, conserva
127.0.0.1:8000 como valor predeterminado. ALLOWED_HOSTS local contiene solamente
localhost, 127.0.0.1 y 192.168.1.20; no contiene comodines. El puerto no se incluye
en ALLOWED_HOSTS. Las credenciales continúan excluidas de Git.

Antes de reiniciar se verificaron PID, comando y directorio del servidor.
Se comprobó HTTP 200 para inicio por la IP Wi-Fi y para acceso con cada host
permitido; un Host ajeno recibe HTTP 400. No se cambiaron bases ni ejecutaron
migraciones. Esta comprobación desde la Mac no garantiza que el router o firewall
permitan la conexión desde el teléfono: la prueba final se hace en el dispositivo.

Si macOS solicita permitir conexiones entrantes para Python, permitirlas para
esta prueba local. Si no conecta, revisar que ambos equipos estén en la misma
red y que no haya aislamiento de clientes/red de invitados. No configurar puertos
en el router. La IP puede cambiar por DHCP; volver a comprobar en0 y actualizar
ALLOWED_HOSTS explícitamente si cambia. DEBUG permanece activo: solo demostración
local con datos ficticios, sin HTTPS ni publicación.

Reiniciar posteriormente: `./iniciar-local.sh` desde GuateBecas, cuando el puerto
esté libre. El registro y PID están en `.local/server.log` y `.local/server.pid`;
el PID debe verificarse antes de detener un proceso.
