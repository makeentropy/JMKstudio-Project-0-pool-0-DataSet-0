from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import os
import threading
from typing import Optional
import sys


class TerminalSession:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.output_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

    def start(self):
        if sys.platform == 'win32':
            cmd = ['cmd.exe']
        else:
            cmd = ['/bin/bash', '-i']
        
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

    def write(self, data: str):
        if self.process and self.process.stdin:
            self.process.stdin.write(data)
            self.process.stdin.flush()

    def read_output(self, callback):
        if self.process:
            while True:
                output = self.process.stdout.readline()
                if output == '' and self.process.poll() is not None:
                    break
                if output:
                    callback(output)

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()


def create_app():
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(__file__), '../../templates'),
                static_folder=os.path.join(os.path.dirname(__file__), '../../static'))
    app.config['SECRET_KEY'] = 'superstring-singularity-quantum-secret-key'
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    terminal = TerminalSession()

    @app.route('/')
    def index():
        return render_template('index.html')

    @socketio.on('connect')
    def handle_connect():
        terminal.start()
        
        def send_output(data):
            emit('output', data, broadcast=False)
        
        terminal.output_thread = threading.Thread(
            target=terminal.read_output,
            args=(send_output,)
        )
        terminal.output_thread.daemon = True
        terminal.output_thread.start()

    @socketio.on('input')
    def handle_input(data):
        terminal.write(data)

    @socketio.on('disconnect')
    def handle_disconnect():
        terminal.stop()

    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'service': 'web-terminal'})

    return app, socketio


if __name__ == '__main__':
    app, socketio = create_app()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
