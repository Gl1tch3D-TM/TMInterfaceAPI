from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
import sys

class MainClient(Client):
    def __init__(self):
         self.TotalAir = 0
         self.time_from = 2800
         self.time_to = 5000


    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_simulation_step(self, iface, _time: int):
        if _time >= self.time_from:
            if self.is_air(iface):
                self.TotalAir += 10
            elif not self.is_air(iface) and _time == self.time_to:
                print(f"Total Airtime: {self.TotalAir}")
                self.TotalAir = 0

    def on_run_step(self, iface, _time: int):
        if _time >= self.time_from:
            if self.is_air(iface):
                self.TotalAir += 10
                print(self.TotalAir)
            elif not self.is_air(iface) and _time == self.time_to:
                print(f"Total Airtime: {self.TotalAir}")
                self.TotalAir = 0

    def is_air(self, iface):
            state = iface.get_simulation_state()
            cur_air = True
            for wheel in state.simulation_wheels:
                if wheel.real_time_state.has_ground_contact:
                    cur_air = False
                    break
            return cur_air


def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface1'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
