# bf_airtime; airtime reduction bruteforce script by Tomashu

from tminterface.client import Client, run_client
from tminterface.interface import TMInterface
from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase

TAG = "[AirTime] "
def getServerName():
    try:
        server_id = abs(int(input(TAG + "Enter the TMInterface instance ID you would like to connect to...\n")))
    except:
        server_id = 0
    finally:
        return f"TMInterface{server_id}"

def log(msg, iface: TMInterface):
    iface.log(TAG + msg)
    print(msg)

class AirTime(Client):
    def __init__(self):
        super().__init__()
        self.time_from = -1
        self.time_to = -1
        self.prev_air = False
        self.mode = 'l'
        self.best = -1
        self.groundtime = 0
        self.current_time = -10000
        self.landing_time = 0
        self.takeoff_time = 0

    def on_registered(self, iface: TMInterface):
        print(TAG + f"Registered to {iface.server_name}")
        iface.execute_command("set controller bruteforce")
        iface.log(TAG + "The script will try to optimize given condition in given time range")
        iface.log(TAG + "Use `landing` command to land as early as possible")
        iface.log(TAG + "`time_from` is mandatory and should be set to time before the landing you want to optimize, it will not optimize further that time")
        iface.log(TAG + "`time_to` is optional and the landing must happen before that time, but doesnt have to in the base run.")
        iface.log(TAG + "Use `airtime` command to reduce total time spent in air")
        iface.log(TAG + "`time_from` is mandatory")
        iface.log(TAG + "`time_to` is mandatory and the run must be less than finish time, even bruteforced finish time")
        iface.log(TAG + "Usage: `time_from landing`")
        iface.log(TAG + "Usage: `time_from-time_to landing`")
        iface.log(TAG + "Usage: `time_from-time_to airtime`")
        iface.register_custom_command("landing")
        iface.register_custom_command("airtime")

    def on_custom_command(self, iface: TMInterface, time_from: int, time_to: int, command: str, args: list):
        msg = ("Invalid command", "error")
        if command == "landing":
            msg = self.on_landing(time_from, time_to)
        if command == "airtime":
            msg = self.on_airtime(time_from, time_to)
        iface.log(TAG + msg[0], msg[1])

    def on_landing(self, time_from: int, time_to: int):
        self.time_from = time_from
        self.time_to = time_to
        self.mode = 'l';
        return "Landing configuration set correctly!", "success"

    def on_airtime(self, time_from: int, time_to: int):
        self.time_from = time_from
        self.time_to = time_to
        self.mode = 'a';
        return "Airtime configuration set correctly!", "success"
    
    def on_simulation_begin(self, iface: TMInterface):
        if self.time_from == -1:
            print(TAG + "Do not forget to set a start time!")
            iface.close()
            return
        if self.time_to == -1 and self.mode == 'a':
            print(TAG + "Do not forget to set an end time!")
            iface.close()
            return
        self.prev_air = False
        self.best = 0 if self.mode == 'a' else -1
        self.current_time = -10000
        self.groundtime = 0

    def is_air(self, iface: TMInterface):
        state = iface.get_simulation_state()
        wheels_in_air = True
        for simulation_wheel in state.simulation_wheels:
            wheels_in_air &= (simulation_wheel.real_time_state.has_ground_contact == 0)
        return wheels_in_air

    def on_bruteforce_evaluate(self, iface: TMInterface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        global num
        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING
        state = iface.get_simulation_state()
        pos = state.position
        if pos[2]>180 and info.time == 18900:
            response.decision = BFEvaluationDecision.REJECT
            return response

        timetravel = self.current_time + 10 != info.time
        self.current_time = info.time
            
        prev_air = self.prev_air
        cur_air = self.is_air(iface)
        self.prev_air = cur_air

        if self.mode == 'a':
            if self.current_time < self.time_from or timetravel:
                self.groundtime = 0
                return response
            if self.current_time > self.time_to or self.groundtime + self.time_to - self.current_time < self.best:
                if info.phase == BFPhase.SEARCH:
                    response.decision = BFEvaluationDecision.REJECT
                return response
            
            if not cur_air:
                self.groundtime += 10

            if self.current_time == self.time_to:
                if self.groundtime > self.best:
                    self.best = self.groundtime
                    if info.phase == BFPhase.INITIAL:
                        print(f"base at {self.groundtime}")
                    elif info.phase == BFPhase.SEARCH:
                        print(f"best at {self.groundtime}")
                        response.decision = BFEvaluationDecision.ACCEPT
                        

        elif self.mode == 'l':
            if self.current_time < 0 or self.current_time <= self.time_from or timetravel:
                return response

            if (self.best >= 0 and self.current_time > self.best) or (self.time_to >= 0 and self.current_time > self.time_to):
                if info.phase == BFPhase.SEARCH:
                    response.decision = BFEvaluationDecision.REJECT
                return response

            if prev_air and not cur_air:
                if self.current_time < self.best or self.best < 0:
                    self.best = self.current_time
                    if info.phase == BFPhase.INITIAL:
                        print(f"base at {self.current_time}")
                    elif info.phase == BFPhase.SEARCH:
                        print(f"best at {self.current_time}")
                        response.decision = BFEvaluationDecision.ACCEPT

        return response        
    
    def on_run_step(self, iface: TMInterface, _time: int):
        # timetravel or init
        if self.current_time > _time or _time < 0:
            self.current_time = _time
            self.landing_time = 0
            self.takeoff_time = 0
            self.prev_air = self.is_air(iface)
            return

        self.current_time = _time
        
        prev_air = self.prev_air
        cur_air = self.is_air(iface)
        self.prev_air = cur_air
        
        if prev_air and not cur_air:
            # landing
            self.landing_time = _time
            log(f"{_time}: landing after {self.landing_time - self.takeoff_time}ms in air", iface)
        if cur_air and not prev_air:
            # takeoff
            self.takeoff_time = _time
            log(f"{_time}: takeoff after {self.takeoff_time - self.landing_time}ms on ground", iface)
    
    def main(self, server_name = getServerName()):
        print(TAG + f"Connecting to {server_name}...")
        run_client(self, server_name)
        print(TAG + f"Deregistered from {server_name}")

if __name__ == "__main__":
    AirTime().main()
