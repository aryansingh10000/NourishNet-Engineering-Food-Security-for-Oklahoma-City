import random
import time
import matplotlib.pyplot as plt
n = int(input("Enter the value of the grid: "))
grid_size = 2 * n + 1
visited = set()
gregarious = set()
direction_mode = "SEW"
p = 0.5
if direction_mode == "SEW":
    directions = [(0, -1), (-1, 0), (1, 0)]
elif direction_mode == "NSEW":
    directions = [(0,1),(0, -1), (-1, 0), (1, 0)]    
elif direction_mode == "ES":
    directions = [(0, -1), (1, 0)]          
elif direction_mode == "S":
    directions = [(0, -1)]                 
for i in range(-n, n + 1):
      gregarious.add((i, -n))
      visited.add((i, -n))
def release_walker():
    i = random.randint(-n, n)
    j = n
    return (i, j)
def move(pos):
    i, j = pos
    di, dj = random.choice(directions)
    ni, nj = i + di, j + dj
    if nj == n + 1:
        nj = -n
    if ni == -n - 1:
        ni = n
    if ni == n + 1:
        ni = -n
    return (ni, nj)
def count_adjacent_gregarious(pos):
    i, j = pos
    count = 0
    for di, dj in directions:
        ni, nj = i + di, j + dj
        if (ni, nj) in gregarious:
            count += 1
    return count
def touches_top_edge():
    for i, j in gregarious:
        if j == n:
            return True
    return False
while not touches_top_edge():
    pos = release_walker()
    print(f"Walker released at {pos}")
    while True:
        pos = move(pos)
        i, j = pos
        if j > n:
            print("Walker lost. restarting")
            break
        visited.add(pos)
        adjacent_count = count_adjacent_gregarious(pos)
        if j == -n:
            gregarious.add(pos)
            print(f"Gregarious walker added at {pos} (bottom edge)")
            break
        elif adjacent_count >= 2:
            gregarious.add(pos)
            print(f"Gregarious walker added at {pos} (adjacent to {adjacent_count} walkers)")
            break
        elif adjacent_count == 1:
            if random.random() < p:
                gregarious.add(pos)
                print(f"Gregarious walker added at {pos} (adjacent to 1 walker, stopped with prob {p})")
                break
            else:
                continue
MAX_AGE = 3  
while not touches_top_edge():
    pos = release_walker()
    age = 0  
    print(f"Walker released at {pos}")
    while True:
        pos = move(pos)
        age += 1
        i, j = pos
        if j > n:
            print("Walker lost. restarting")
            break
        visited.add(pos)
        adjacent_count = count_adjacent_gregarious(pos)
        if j == -n:
            gregarious.add(pos)
            print(f"Gregarious walker added at {pos} (bottom edge)")
            break
        elif adjacent_count >= 2:
            gregarious.add(pos)
            print(f"Gregarious walker added at {pos} (adjacent to {adjacent_count} walkers)")
            break
        elif adjacent_count == 1:
            if random.random() < p:
                gregarious.add(pos)
                print(f"Gregarious walker added at {pos} (adjacent to 1 walker, stopped with prob {p})")
                break
        if age >= MAX_AGE:
            print(f"Walker died of old age at {pos}")
            break
x_g, y_g = zip(*gregarious)
x_v, y_v = zip(*visited)
plt.figure(figsize=(6, 6))
plt.scatter(x_v, y_v, c='lightgray', s=10, label='Visited')
plt.scatter(x_g, y_g, c='red', s=20, label='Gregarious')
plt.legend()
plt.title(f"Gregarious Walkers Simulation Variant (p={p})")
plt.grid(True)
plt.axis('equal')
plt.show()
total_nodes = grid_size * grid_size
fraction_occupied = len(gregarious) / total_nodes
print(f"Fraction of nodes occupied: {fraction_occupied:.4f}")
