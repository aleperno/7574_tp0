from multiprocessing import Process, active_children, Queue
import logging
import os


def decorator(queue, target, *args):
    """
    Decorates a function to be called

    :param Queue queue: The Queue to report to
    :param function target: The function to execute
    :param args: The args to be passed to the function

    This decorator calls a given function with the given args.
    After the call completes, it sends a message to the queue to notify its completion
    """
    logging.debug("Recibi queue: %r, target: %r, args: %r", queue, target, args)
    target(*args)
    pid = os.getpid()
    msg = {
        'op': 'fin',
        'pid': pid
    }
    logging.debug("Process %s finished", pid)
    queue.put(msg)


class PoolClosedException(Exception):
    pass


class CustomPool:
    def __init__(self, processes=os.cpu_count()):
        self.max_processes = processes
        self.pending_tasks = Queue()
        self.queue = Queue()
        self.handler_process = Process(target=self._run)
        self.counter = 0
        self.handler = False
        self.accept_new = False
        self.running = False
        self.process_tracker = set()

    def _end_handler(self):
        """
        If the current process is the handler process (not the main process):
            - Terminate any active children
            - Call the destroy remaining tasks method
        """
        if self.handler:
            # Must wait for any spawned processes
            logging.debug("Terminating spawned processes")
            for process in active_children():
                process.terminate()
            self._destroy_remaining_tasks()

    def _join_handler(self):
        """
        If the current process if the handler process (not the main process):
            - Wait for any active children
            - Set the `running` flag to false
        """
        if self.handler:
            # Must wait for any spawned processes
            logging.debug("Waiting for any spawned processes")
            for process in active_children():
                process.join()
            self.running = False

    def _destroy_remaining_tasks(self):
        """
        For any task remaining in the pending tasks queue, if the task has a defined destroyer
        call it with the task args.
        """
        while not self.pending_tasks.empty():
            target, args, destroyer = self.pending_tasks.get()
            if destroyer:
                destroyer(*args)

    def _run(self):
        """
        Main loop of the handler process

        While the running flag is set, it will read messages from the queue and calling the
        apropiate methods based on the message
        """

        # Initialize multiple flags

        # This current process is the handler
        self.handler = True
        # We are running
        self.running = True
        # and accepting new child processes
        self.accept_new = True

        logging.debug("Running in %s", os.getpid())

        while self.running:
            msg = self.queue.get()
            logging.debug("Received message %r", msg)
            op = msg.get('op')

            if op == 'new':
                # Try to spawn a new process
                self._new_process(msg['target'], msg['args'], msg['destroyer'])
            elif op == 'fin':
                # A child process has just finished
                self._process_end(msg['pid'])
            elif op == 'die':
                # We must terminate all processes
                self.accept_new = False
                self._end_handler()
            elif op == 'join':
                # We must wait for all processes
                self._join_handler()
        logging.debug("Exiting Worker Pool")

    def _new_process(self, target, args, destroyer):
        """
        Queues a new task
        """

        # No new processes are allowed, an exception is raised
        if not self.accept_new:
            raise PoolClosedException

        if self.counter == self.max_processes:
            # Limit reached, the task is queued in the pending tasks queue
            self.pending_tasks.put((target, args, destroyer))
            logging.debug("No more space for new processes")
        else:
            # Can spawn it
            logging.debug("Will spawn a new process")

            # We will use a decorator that requires a queue to report after the task is completed
            new_args = (self.queue, target) + args
            # Spawn and start the process
            process = Process(target=decorator, args=new_args)
            process.daemon = True
            process.start()

            # Increase the control counter and add the process to the tracker
            self.counter += 1
            self.process_tracker.add(process.pid)
            logging.info("Started new process %s", process.pid)

    def _process_end(self, pid):
        """
        Process task completion
        """

        if pid not in self.process_tracker:
            # The process id is not found in the tracker, therefore won't decrease the counter
            logging.debug("Process not found in the tracker")
        else:
            # Remove the pid from the tracker and decrease the counter
            self.process_tracker.remove(pid)
            self.counter -= 1

            # If pending tasks, get one from the queue and start the process
            if not self.pending_tasks.empty() and self.accept_new:
                target, args, destroyer = self.pending_tasks.get()
                self._new_process(target, args, destroyer)

    # THESE ARE THE PRIMITIVES THAT WILL BE USED DIRECTLY BY THE MAIN INSTANCE OF THIS CLASS
    def start(self):
        """
        Start the handler process
        """
        self.handler_process.start()

    def apply_async(self, target, args, destroyer=None):
        """
        Queues a function to be executed

        :param target: Function to be called
        :param args: Arguments to call the function
        :param destroyer: Optional method. Should accept the same arguments as `target`.
            If defined, the destroyer will be called if the function was not executed and
            the Pool is being terminated

        Queues a function to be called by the Pool
        """
        msg = {
            'op': 'new',
            'target': target,
            'args': args,
            'destroyer': destroyer,
        }
        self.queue.put(msg)

    def terminate(self):
        """
        Sends a message to the Pool to terminate all processes
        """
        self.queue.put({'op': 'die'})

    def join(self):
        """
        Sends a message to the Pool to wait for all processes
        and then waits for the handler process
        """
        self.queue.put({'op': 'join'})
        self.handler_process.join()
