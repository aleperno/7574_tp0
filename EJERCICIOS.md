# Ejercicios

## Ejercicio 1

```
Definir un script que permita crear una definicion de docker-compose con cantidad de clientes N
```

### Solucion

- Ejecutar `bash ej1.sh <numero`
- Tambien se podria hacer `docker-compose -f docker-compose-dev.yaml --scale client=5 -d` previa modificacion del compose para que el nombre del container no sea custom

## Ejercicio 2

```
Modificar el cliente y el servidor para lograr que realizar cambios en el archivo de configuración no requiera un nuevo build de las imágenes de Docker para que los mismos sean efectivos. La configuración a través del archivo debe ser injectada al ejemplo y persistida afuera del mismo. (Hint: docker volumes)
```

### Solucion

- Se agregó en cada servicio un volumen para que sobre-escriba el archivo de configuracion
- En el servicio de GO se borraron las variables de entorno que sobre-escriben lo leido por el archivo

## Ejercicio 3

```
Crear un script que permita testear el correcto funcionamiento del servidor utilizando el
comando **netcat**. Dado que el servidor es un EchoServer, se debe enviar un mensaje el servidor
y esperar recibir el mismo mensaje enviado.

Netcat no debe ser instalado en la maquina y no se puede exponer puertos del
servidor para realizar la comunicación. (Hint: docker network)
```

### Solucion

- Se creó un script `script.sh` que emplea netcat, envia un mensaje y luego compara la respuesta contra un template

- Para emplear el script, se construyó una imagen de docker basada en el mismo python que el server, con el agregado que se instala el packete de netcat

- Se agrega un script `ej3.sh` con todos los comandos necesarios. Si se desea hacer a mano se debe hacer

  - Buildear la imagen `docker build . -t nctest`

  - Correrla 

    ```
    docker run --rm --name ej3 -v $(pwd)/script.sh:/script.sh --network=tp0_testing_net nctest script.sh
    ```

    Este comando lo que hace es

    - `--rm`: Elimina el container una vez terminada la ejecución
    - `--name eje`: Nombre del container para facilitar su identificación
    - `-v $(pwd)/script.sh:/script.sh`: Monta el script del directorio local, en el root del container
    - `--network=tp0_testing_net`: A que red va a estar asociada el container. En este caso la misma red que se define en el compose del cliente/servidor
    - `nctest`: El nombre de la imagen a utulizar
    - `script.sh` Será nuestro entrypoint, es decir una vez que "arranque" el container se ejecutará dicho script

## Ejercicio 4

```
Modificar cliente o servidor (no es necesario modificar ambos) para que el programa termine de forma gracefully al recibir la signal SIGTERM. Terminar la aplicación de forma gracefully implica que todos los sockets y threads/procesos de la aplicación deben cerrarse/joinearse antes que el thread de la aplicación principal muera. Loguear mensajes en el cierre de cada recurso.(Hint: Verificar que hace el flag -t utilizado en comando docker-compose-down)
```

### Solución

- Se modificó el entrypoint de `docker-compose` para mejor manejo de señales [leer faq](https://docs.docker.com/compose/faq/#why-do-my-services-take-10-seconds-to-recreate-or-stop)
- Se agregó handleo de **SIGTERM**:
  - La clase `Server` ahora posee un método `sigterm_handler` que es registrado para manejar los sigterms. El método lo único que hace es raiser una excepción custom `SigtermException`
  - Los métodos `run` y `__handle_client_connection` ahora manejan esta excepción.
    - `__handle_client_connection`: Si recibe una señal mientras espera recibir un mensaje del cliente, cierra el socket.
    - `run`: Al recibir una señal mientras acepta nuevos clientes, deja de aceptar nuevos y procede a terminar todos los procesos (ver siguiente ejercicio)

## Ejercicio 5

```
Modificar el servidor actual para que el mismo permita procesar mensajes y aceptar nuevas conexiones en paralelo.

El alumno puede elegir el lenguaje en el cual desarrollar el nuevo código del servidor. Si el alumno desea realizar las modificaciones en Python, tener en cuenta las limitaciones del lenguaje.
```

### Solución

El server posee dos responsabilidades aceptar nuevos clientes y manejar la comunicación con los mismos. Ahora esto se hace en procesos diferentes.

- El proceso "padre" aceptará las nuevas conexiones de los clientes. Por cada conexión recibida *spawneará* un nuevo proceso que será el encargado de administrar la comunicación con el mismo. Al recibir un **SIGTERM**, se procede a terminar todos los subprocesos aún activos.
- Los procesos "hijos" recibiran una conexión ya establecida con el cliente y manejarán la comunicación con el mismo. En caso de recibir un **SIGTERM** cerrarán la conexión, habiendo o no recibido mensajes.

### UPDATED

Dada la hipotética situación en la que una cantidad creciente de clientes nos haga spawnear demasiados procesos, se estableció la utilización de un Pool de procesos, que spawneará tantos procesos como procesadores tengamos disponibles.

Se implementó una clase Pool custom, dado que la clase Pool del modlulo multiprocessing carecía de algunas funcionalidades deseables (o quizá falta de conocimiento mia)

- Cuando un subproceso handleaba un SIGTERM, el procesos padre se colgaba
- No hay (o no econtré) forma de establecer un destructor para las tareas pendientes de ejecución en el Pool, por lo tanto no podriamos asegurarnos la liberación adecuada de recursos reservados para dichas tareas
