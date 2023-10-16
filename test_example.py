def sum(int1, int2):
    return int1 + int2


expected_output = 5
actual_output = sum(2, 3)

assert expected_output == actual_output, f"Expected {expected_output} but got {actual_output}"
print("Test passed")