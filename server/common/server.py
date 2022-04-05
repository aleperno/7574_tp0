import socket
import logging
import signal
import os
from .pool import CustomPool
#from multiprocessing import Pool, active_children, cpu_count


class SigtermException(Exception):
    pass


def handle_client(client_sock):
    """
    Read message from a specific client socket and closes the socket

    If a problem arises in the communication with the client, the
    client socket will also be closed

    If a SIGTERM is received, log the event and close the socket.
    """
    pid = os.getpid()
    logging.info("Client Handler spawned %s", pid)
    try:
        msg = client_sock.recv(1024).rstrip().decode('utf-8')
        logging.info(
            'Message received from connection {}. Msg: {}'
                .format(client_sock.getpeername(), msg))
        client_sock.send("Your Message has been received: {}\n".format(msg).encode('utf-8'))
    except OSError:
        logging.info("Error while reading socket {}".format(client_sock))
    except SigtermException:
        logging.info("Process %s received SIGTERM", pid)
    finally:
        client_sock.close()


def client_cleaner(client_sock):
    """
    Given a client sock, it closes it
    """
    client_sock.close()


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

    @staticmethod
    def client_cleaner(client_sock):
        client_sock.close()

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """
        logging.info("Started Server process at %s", os.getpid())
        pool = CustomPool(processes=os.environ.get('MAX_PROCESSES', os.cpu_count()))
        pool.start()
        try:
            while True:
                client_sock = self.__accept_new_connection()
                pool.apply_async(target=handle_client,
                                 args=(client_sock,),
                                 destroyer=client_cleaner)
        except SigtermException:
            logging.info("Gracefully shutting down server")
            pool.terminate()
            pool.join()

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
