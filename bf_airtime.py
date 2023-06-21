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
    """Main Client Implementation."""
    def __init__(self):
        self.time_from = -1
        self.time_to = -1
        self.prev_air = False
        self.best = -1
        self.current_time = -10000
        self.landing_time = 0
        self.takeoff_time = 0

    def on_registered(self, iface: TMInterface):
        print(TAG + f"Registered to {iface.server_name}")
        iface.execute_command("set controller bruteforce")
        iface.log(TAG + "The script will try to optimize the first airtime after start_time")
        iface.log(TAG + "Use the airtime command to set start time: `time_from airtime`")
        iface.log(TAG + "Use the airtime command to set evaluation time: `time_from-time_to airtime`")
        iface.register_custom_command("airtime")

    def on_custom_command(self, iface: TMInterface, time_from: int, time_to: int, command: str, args: list):
        msg = ("Invalid command", "error")
        if command == "airtime":
            msg = self.on_airtime(time_from, time_to)
        iface.log(TAG + msg[0], msg[1])

    def on_airtime(self, time_from: int, time_to: int):
        self.time_from = time_from
        self.time_to = time_to
        return "Airtime start time changed correctly!", "success"

    def on_simulation_begin(self, iface: TMInterface):
        if self.time_from == -1:
            print(TAG + "Do not forget to set a start time!")
            iface.close()
            return
        self.prev_air = False
        self.best = -1
        self.current_time = -10000

    def is_air(self, iface: TMInterface):
        state = iface.get_simulation_state()
        wheels_in_air = True
        for simulation_wheel in state.simulation_wheels:
            wheels_in_air &= (simulation_wheel.real_time_state.has_ground_contact == 0)
        return wheels_in_air

    def on_bruteforce_evaluate(self, iface: TMInterface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING

        timetravel = self.current_time + 10 != info.time
        self.current_time = info.time
            
        prev_air = self.prev_air
        cur_air = self.is_air(iface)
        self.prev_air = cur_air
            
        if info.time < 0 or info.time == self.time_from or info.time < self.time_from or timetravel:
            return response
        
        if (self.best > 0 and self.current_time > self.best) or (self.time_to > 0 and self.current_time > self.time_to):
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
