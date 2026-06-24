"""
Stego Terminal - interactive CLI for the steganographic memory system.

Commands:
    node      - Manage base nodes (list, create, info, tag, kill)
    probe     - Manage probes (list, create, encode, decode)
    matrix    - Query the singularity matrix (stats, query, anchors, tags)
    pool      - Manage dimension space pool (spaces, datasets)
    agent     - Manage AI agents (start, stop, status, goals)
    okr       - Manage OKRs (objectives, key results, progress)
    log       - View logic logs
    help      - Show help
    exit      - Exit terminal
"""

import cmd
import sys
import json
from typing import Optional

from ..utils import CA, LogicLogger
from ..base_node import ProcessManager, NodeRegistry
from ..memory_matrix import SingularityMatrix, MemoryPool
from ..probe import ProbeManager
from ..ai_agent import StegoAgent, SelfTrainer, OKR
from ..data_science import FileManager, DataOrder


class StegoTerminal(cmd.Cmd):
    intro = """
╔══════════════════════════════════════════════════════════════╗
║   Quantum Steganographic Memory Execution System            ║
║   隐写内存执行系统 - Data Science Terminal                  ║
║                                                              ║
║   Type 'help' for available commands                        ║
╚══════════════════════════════════════════════════════════════╝
"""
    prompt = "stego> "

    def __init__(self):
        super().__init__()
        self.ca = CA("ROOT_CA")
        self.logger = LogicLogger("singularity_system")
        self.matrix = SingularityMatrix("primary", self.logger)
        self.pool = MemoryPool("dimension_pool", self.logger)
        self.process_mgr = ProcessManager(self.ca, self.logger)
        self.registry = NodeRegistry(self.ca, self.logger)
        self.probe_mgr = ProbeManager(self.ca, self.pool, self.logger)
        self.agent: Optional[StegoAgent] = None
        self.trainer: Optional[SelfTrainer] = None
        self.okr = OKR("system")
        self.file_mgr = FileManager()
        self.data_order = DataOrder()
        self._init_defaults()

    def _init_defaults(self):
        proc = self.process_mgr.spawn("core_validator", matrix=self.matrix)
        if proc:
            proc.node.add_tag("core")
            proc.node.add_tag("validator")
            self.registry.register(proc.node)

        self.probe_mgr.create_probe("probe_alpha")
        self.probe_mgr.create_probe("probe_beta")

        self.pool.create_space("data_science")
        self.pool.create_space("ai_research")

        obj = self.okr.create_objective(
            "Build steganographic memory system",
            "Complete implementation of all core modules"
        )
        self.okr.add_key_result(obj.obj_id, "base_node module", 1.0)
        self.okr.add_key_result(obj.obj_id, "steganography module", 1.0)
        self.okr.add_key_result(obj.obj_id, "memory_matrix module", 1.0)
        self.okr.add_key_result(obj.obj_id, "probe module", 1.0)
        self.okr.add_key_result(obj.obj_id, "ai_agent module", 1.0)
        self.okr.update_key_result("kr_0001", value=1.0)
        self.okr.update_key_result("kr_0002", value=1.0)
        self.okr.update_key_result("kr_0003", value=1.0)
        self.okr.update_key_result("kr_0004", value=1.0)
        self.okr.update_key_result("kr_0005", value=1.0)

    def _print_json(self, data):
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))

    def do_node(self, arg):
        """Node management: node <list|create|info|tag|kill> [args]"""
        parts = arg.split()
        if not parts:
            print("Usage: node <list|create|info|tag|kill> [args]")
            return

        cmd = parts[0]
        if cmd == "list":
            ps = self.process_mgr.ps()
            self._print_json(ps)
        elif cmd == "create":
            name = parts[1] if len(parts) > 1 else "unnamed"
            proc = self.process_mgr.spawn(name, matrix=self.matrix)
            if proc:
                print(f"Created node: {proc.pid} ({name})")
                self.registry.register(proc.node)
            else:
                print("Failed to create node")
        elif cmd == "info":
            if len(parts) < 2:
                print("Usage: node info <pid>")
                return
            proc = self.process_mgr.get(parts[1])
            if proc:
                self._print_json(proc.node.get_status())
            else:
                print("Node not found")
        elif cmd == "tag":
            if len(parts) < 3:
                print("Usage: node tag <pid> <tag>")
                return
            proc = self.process_mgr.get(parts[1])
            if proc:
                proc.node.add_tag(parts[2])
                print(f"Added tag '{parts[2]}' to {parts[1]}")
            else:
                print("Node not found")
        elif cmd == "kill":
            if len(parts) < 2:
                print("Usage: node kill <pid>")
                return
            if self.process_mgr.kill(parts[1]):
                self.process_mgr.reap()
                print(f"Killed node {parts[1]}")
            else:
                print("Node not found")
        else:
            print(f"Unknown node command: {cmd}")

    def do_probe(self, arg):
        """Probe management: probe <list|create|encode|decode> [args]"""
        parts = arg.split()
        if not parts:
            print("Usage: probe <list|create|encode|decode> [args]")
            return

        cmd = parts[0]
        if cmd == "list":
            self._print_json(self.probe_mgr.list_probes())
        elif cmd == "create":
            name = parts[1] if len(parts) > 1 else "probe_new"
            probe = self.probe_mgr.create_probe(name)
            print(f"Created probe: {probe.probe_id} ({name})")
        elif cmd == "encode":
            if len(parts) < 3:
                print("Usage: probe encode <probe_name> <data>")
                return
            name = parts[1]
            data = " ".join(parts[2:]).encode()
            req = self.probe_mgr.generate_probe_request(name, data, tag="test")
            if req:
                print(f"Encoded with anchor: {req['anchor']}")
                print(f"  payload hash: {req['payload_hash'][:16]}...")
            else:
                print("Encode failed")
        elif cmd == "stats":
            self._print_json(self.probe_mgr.stats())
        else:
            print(f"Unknown probe command: {cmd}")

    def do_matrix(self, arg):
        """Matrix queries: matrix <stats|query|anchors|tags|sources>"""
        parts = arg.split()
        cmd = parts[0] if parts else "stats"

        if cmd == "stats":
            self._print_json(self.matrix.stats())
        elif cmd == "anchors":
            print("Anchors:", ", ".join(self.matrix.anchors) or "(none)")
        elif cmd == "tags":
            print("Tags:", ", ".join(self.matrix.tags) or "(none)")
        elif cmd == "sources":
            print("Sources:", ", ".join(self.matrix.sources) or "(none)")
        elif cmd == "query":
            tag = parts[1] if len(parts) > 1 else None
            cells = self.matrix.query(tag=tag, limit=10)
            print(f"Found {len(cells)} cells")
            for c in cells:
                data_preview = str(c.data)[:60]
                print(f"  [{c.cell_id}] anchor={c.anchor} tag={c.tag} "
                      f"v{c.version} data={data_preview}...")
        else:
            print(f"Unknown matrix command: {cmd}")

    def do_pool(self, arg):
        """Dimension pool: pool <spaces|datasets|create_space|create_dataset>"""
        parts = arg.split()
        cmd = parts[0] if parts else "spaces"

        if cmd == "spaces":
            self._print_json(self.pool.list_spaces())
        elif cmd == "stats":
            self._print_json(self.pool.stats())
        elif cmd == "create_space":
            name = parts[1] if len(parts) > 1 else "new_space"
            space = self.pool.create_space(name)
            print(f"Created space: {space.space_id} ({name})")
        elif cmd == "datasets":
            space_name = parts[1] if len(parts) > 1 else None
            if not space_name:
                print("Usage: pool datasets <space_name>")
                return
            space = self.pool.get_space(space_name)
            if space:
                self._print_json(space.list_datasets())
            else:
                print("Space not found")
        else:
            print(f"Unknown pool command: {cmd}")

    def do_agent(self, arg):
        """AI agent management: agent <start|stop|status|goals|train>"""
        parts = arg.split()
        cmd = parts[0] if parts else "status"

        if cmd == "start":
            if not self.agent:
                self.agent = StegoAgent("alpha_agent", self.ca,
                                        matrix=self.matrix,
                                        pool=self.pool,
                                        probe_mgr=self.probe_mgr,
                                        logger=self.logger)
                self.trainer = SelfTrainer(self.matrix, self.logger)
            self.agent.start()
            self.trainer.start()
            print("Agent started")
        elif cmd == "stop":
            if self.agent:
                self.agent.stop()
            if self.trainer:
                self.trainer.stop()
            print("Agent stopped")
        elif cmd == "status":
            if self.agent:
                self._print_json(self.agent.get_status())
            else:
                print("No agent running. Use 'agent start' to create one.")
        elif cmd == "goals":
            if self.agent:
                self._print_json({"goals": self.agent.goals})
            else:
                print("No agent running")
        elif cmd == "insights":
            if self.trainer:
                self._print_json(self.trainer.get_insights())
            else:
                print("No trainer running")
        else:
            print(f"Unknown agent command: {cmd}")

    def do_okr(self, arg):
        """OKR management: okr <summary|objectives|add_obj|add_kr|update>"""
        parts = arg.split()
        cmd = parts[0] if parts else "summary"

        if cmd == "summary":
            self._print_json(self.okr.summary())
        elif cmd == "objectives":
            for obj in self.okr.objectives:
                print(f"  [{obj.obj_id}] {obj.title} - "
                      f"{obj.progress*100:.0f}% ({obj.status.value})")
        elif cmd == "add_obj":
            if len(parts) < 2:
                print("Usage: okr add_obj <title>")
                return
            title = " ".join(parts[1:])
            obj = self.okr.create_objective(title)
            print(f"Created objective: {obj.obj_id}")
        elif cmd == "add_kr":
            if len(parts) < 4:
                print("Usage: okr add_kr <obj_id> <title> <target>")
                return
            obj_id = parts[1]
            target = float(parts[-1])
            title = " ".join(parts[2:-1])
            kr = self.okr.add_key_result(obj_id, title, target_value=target)
            if kr:
                print(f"Added KR: {kr.kr_id}")
            else:
                print("Objective not found")
        elif cmd == "update":
            if len(parts) < 3:
                print("Usage: okr update <kr_id> <value>")
                return
            kr_id = parts[1]
            value = float(parts[2])
            if self.okr.update_key_result(kr_id, value=value):
                print(f"Updated {kr_id} to {value}")
            else:
                print("KR not found")
        else:
            print(f"Unknown okr command: {cmd}")

    def do_log(self, arg):
        """View logic logs: log [module] [action] [limit]"""
        parts = arg.split()
        module = parts[0] if len(parts) > 0 else None
        action = parts[1] if len(parts) > 1 else None
        limit = int(parts[2]) if len(parts) > 2 else 20

        entries = self.logger.get_entries(module=module, action=action)
        entries = entries[-limit:]
        print(f"Showing {len(entries)} log entries (chain valid: {self.logger.verify_chain()})")
        for e in entries:
            print(f"  [{e.iteration:04d}] {e.module}.{e.action} "
                  f"- {list(e.payload.keys())}")

    def do_file(self, arg):
        """File management: file <scan|list|search|stats> [args]"""
        parts = arg.split()
        cmd = parts[0] if parts else "stats"

        if cmd == "scan":
            path = parts[1] if len(parts) > 1 else "."
            recs = self.file_mgr.scan_directory(path)
            print(f"Scanned {len(recs)} files")
        elif cmd == "list":
            strategy = parts[1] if len(parts) > 1 else "by_name"
            from . import OrderStrategy
            try:
                strat = OrderStrategy(strategy)
            except ValueError:
                strat = OrderStrategy.BY_NAME
            files = self.file_mgr.list_all(strategy=strat)
            print(f"Total files: {len(files)}")
            for f in files[:20]:
                print(f"  {f.name:40s} {f.size:>10d} bytes")
        elif cmd == "search":
            if len(parts) < 2:
                print("Usage: file search <query>")
                return
            query = " ".join(parts[1:])
            results = self.file_mgr.search(query)
            print(f"Found {len(results)} files")
            for f in results[:20]:
                print(f"  {f.path}")
        elif cmd == "stats":
            self._print_json(self.file_mgr.stats())
        else:
            print(f"Unknown file command: {cmd}")

    def do_status(self, arg):
        """Show overall system status"""
        status = {
            "matrix": self.matrix.stats(),
            "pool": self.pool.stats(),
            "processes": self.process_mgr.count,
            "probes": self.probe_mgr.count,
            "registry": self.registry.size,
            "log_entries": self.logger.chain_length,
            "log_valid": self.logger.verify_chain(),
            "log_iteration": self.logger.iteration,
            "okr_progress": f"{self.okr.overall_progress * 100:.1f}%",
            "agent_running": self.agent is not None and self.agent.consciousness.is_running if self.agent else False,
        }
        self._print_json(status)

    def do_exit(self, arg):
        """Exit the terminal"""
        print("Shutting down steganographic memory system...")
        if self.agent:
            self.agent.stop()
        if self.trainer:
            self.trainer.stop()
        print("Goodbye.")
        return True

    def do_quit(self, arg):
        """Exit the terminal"""
        return self.do_exit(arg)

    def do_help(self, arg):
        """Show help"""
        print("\nAvailable commands:")
        print("  status      - Overall system status")
        print("  node        - Node management (list|create|info|tag|kill)")
        print("  probe       - Probe management (list|create|encode|stats)")
        print("  matrix      - Matrix queries (stats|query|anchors|tags|sources)")
        print("  pool        - Dimension pool (spaces|stats|create_space|datasets)")
        print("  agent       - AI agent (start|stop|status|goals|insights)")
        print("  okr         - OKR management (summary|objectives|add_obj|add_kr|update)")
        print("  file        - File management (scan|list|search|stats)")
        print("  log         - View logic logs")
        print("  help        - Show this help")
        print("  exit/quit   - Exit terminal\n")


def main():
    """Entry point for the CLI terminal."""
    terminal = StegoTerminal()
    try:
        terminal.cmdloop()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
