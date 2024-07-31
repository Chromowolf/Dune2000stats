import numpy as np

NUM_UNITS = 30
NUM_BUILDINGS = 62

LIGHT_INFANTRY_INDEX = 0
HARVESTER_INDEX = 8
MCV_INDEX = 12
DEVIATOR_INDEX = 14

ATREIDES_REFINERY_INDEX = 20
HARKONNEN_REFINERY_INDEX = 21
ORDOS_REFINERY_INDEX = 22

BARRACKS_BUILDING_GROUP_INDEX = 4
LIGHT_FACTORY_BUILDING_GROUP_INDEX = 13
HEAVY_FACTORY_BUILDING_GROUP_INDEX = 15

unit_cost_default = np.array([
    50, 90, 400, 200, 120,
    300, 350, 400, 1200, 700,
    700, 700, 2000, 900, 1000,
    700, 1000, 1050, 1100, 1100,
    0, 0, 0, 0, 0,
    650, 650, 80, 400, 200,
])


unit_build_speed_default = np.array([
    180, 132, 90, 90, 120,
    50, 50, 35, 18, 26,
    26, 26, 15, 22, 20,
    30, 20, 18, 15, 15,
    2, 5, 5, 5, 2,
    30, 30, 120, 50, 70,
])

# unit_build_time_ticks_h1 = [
#     51, 69, 102, 102, 76,
#     184, 184, 264, 512, 354,
#     354, 354, 622, 418, 460,
#     307, 460, 512, 622, 622,
#     4608, 1920, 1920, 1920,
#     4608, 307, 307, 76, 184, 131
# ]

# building_build_time_ticks_h1 = [
#    23040, 23040, 23040, 23040, 51, 51, 51, 76, 76, 76,
#    170, 170, 170, 219, 219, 219, 219, 51, 51, 51,
#    512, 512, 512, 219, 219, 219, 256, 256, 256, 256,
#    256, 256, 384, 384, 384, 264, 264, 264, 128, 128,
#    128, 622, 622, 622, 622, 622, 512, 512, 512, 512,
#    307, 307, 307, 256, 256, 256, 768, 768, 768, 768,
#    256, 256,
#    1, 1, 1, 1, 1, 1, 1, 1,
#    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
#    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
#    1, 1, 1, 1, 1, 1, 1, 1, 1, 1
# ]

weight_infantry = 0.1
weight_light = 0.3
weight_heavy = 0.6

effi_infantry_index = np.array([0, 1, 2, 3, 4, 27, 29])
effi_light_index = np.array([5, 6, 7, 28])
effi_heavy_index = np.arange(8, 18)
effi_all_unit_index = np.concatenate((effi_infantry_index,
                                      effi_light_index,
                                      effi_heavy_index))
effi_unit_weights = np.zeros(NUM_UNITS)  # (30, )
effi_unit_weights[effi_infantry_index] = weight_infantry
effi_unit_weights[effi_light_index] = weight_light
effi_unit_weights[effi_heavy_index] = weight_heavy

assert len(effi_all_unit_index) == 21, f"Should be 21 units types to calculate efficiency. Got {effi_all_unit_index}"

effi_all_building_index = np.concatenate((
    np.arange(10, 16),
    np.arange(20, 62),
))

unit_cost_easy = unit_cost_default * 75 // 100
unit_cost_hard = unit_cost_default * 125 // 100

unit_cost_array = np.vstack((unit_cost_easy, unit_cost_default, unit_cost_hard))

max_build_boost = 125 + 125
unit_build_time_ticks_default = 23040 // (max_build_boost * unit_build_speed_default // 100)


if __name__ == "__main__":
    print(unit_cost_default)
    print(unit_build_time_ticks_default)
