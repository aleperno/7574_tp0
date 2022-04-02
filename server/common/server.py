import socket
import logging
import signal


class SigtermException(Exception):
    pass

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        signal.signal(signal.SIGTERM, self.sigterm_handler)
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._server_socket.close()

    def sigterm_handler(self, signum, frame):
        """
        Handler for SIGTERM signal

        This handler will be used for both the main server process accepting new connections and
        the server subprocesses handling clients' messages.

        Since `socket.accept` is blocking, the only way to break the loop is raising an exception.
        """
        logging.info("Received SIGTERM")
        raise SigtermException

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        try:
            while True:
                client_sock = self.__accept_new_connection()
                self.__handle_client_connection(client_sock)
        except SigtermException:
            logging.info("Gracefully shutting down server")
            if 'client_sock' in locals():
                # I don't like this a single bit. But there's not much else I can do, besides
                # initializing 'client_sock' with a dummy object that takes a `close` method
                # WHY? There's a slim change we get a SIGINT after accepting a new connection,
                # but before we handled that client connection. Therefore that client socket
                # will still be open.
                # If the handler had already closed the socket, it's ok since the `close` is idempotent
                # and performing a close in an already closed socket raises no errors
                client_sock.close()

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            msg = client_sock.recv(1024).rstrip().decode('utf-8')
            logging.info(
                'Message received from connection {}. Msg: {}'
                .format(client_sock.getpeername(), msg))
            client_sock.send("Your Message has been received: {}\n".format(msg).encode('utf-8'))
        except OSError:
            logging.info("Error while reading socket {}".format(client_sock))
        finally:
            client_sock.close()

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info("Proceed to accept new connections")
        c, addr = self._server_socket.accept()
        logging.info('Got connection from {}'.format(addr))
        return c
