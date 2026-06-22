*This project has been created as part of the 42 curriculum by kpanfero.*

---

# Codexion - Dongle-based Coder Simulation

Codexion is a multithreaded simulation in C that models a group of software developers (coders) competing for limited shared resources (dongles) to perform compilation tasks. The project explores classic concurrency control problems, thread synchronization, and scheduling algorithms (FIFO and EDF) in a practical, deadlock-free environment.

---

## :book: Description

The simulation consists of `N` coders arranged in a circle, where each coder requires **two adjacent dongles** to compile code. Each coder repeatedly:
1. Acquires two dongles (in a fixed order to prevent deadlocks).
2. Compiles for a fixed duration.
3. Releases the dongles (with a cooldown period).
4. Spends time debugging and refactoring.

The simulation monitors two termination conditions:
- **All coders complete** their required number of compilations.
- **Any coder burns out** if they spend more than `time_to_burnout` milliseconds without starting a compilation.

Two scheduling policies are supported for dongle allocation:
- **FIFO (First In, First Out)**: Coders are served in the order they request dongles.
- **EDF (Earliest Deadline First)**: Coders with the closest burnout deadline are prioritized.

This project serves as a hands-on demonstration of thread safety, priority queues, and real-time scheduling concepts in C using the pthread library.

---

## :gear: Instructions

### :file_folder: Compilation

To compile the project, run:

```bash
cc -Wall -Wextra -Werror -pthread codexion_main.c codexion_coder.c codexion_dongle.c codexion_heap.c codexion_heap2.c codexion_init.c codexion_monitor.c codexion_utils.c -o codexion
Or use the provided Makefile (if available):

bash
make
:arrow_forward: Execution
Run the simulation with the following syntax:

bash
./codexion <num_coders> <time_to_burnout> <time_to_compile> <time_to_debug> <time_to_refactor> <compiles_required> <dongle_cooldown> <scheduler>
Arguments
Argument	Description
num_coders	Number of coders (and dongles) in the simulation.
time_to_burnout	Max time (ms) a coder can go without compiling before burning out.
time_to_compile	Time (ms) a coder spends compiling.
time_to_debug	Time (ms) a coder spends debugging after compilation.
time_to_refactor	Time (ms) a coder spends refactoring after debugging.
compiles_required	Number of compilations each coder must complete.
dongle_cooldown	Cooldown time (ms) after a dongle is released before it can be reused.
scheduler	Scheduling policy: fifo or edf.
Example
bash
./codexion 5 1000 200 150 100 3 50 fifo
This runs a simulation with:

5 coders

1000ms burnout time

200ms compile time

150ms debug time

100ms refactor time

3 compilations required per coder

50ms dongle cooldown

FIFO scheduling

:outbox_tray: Output
The program outputs log messages in the format:

text
<timestamp_ms> <coder_id> <action>
Example output:

text
15 1 has taken a dongle
16 1 has taken a dongle
17 1 is compiling
220 1 is debugging
370 1 is refactoring
470 2 has taken a dongle
...
:thread: Thread Synchronization Mechanisms
Codexion uses the following pthread primitives to ensure thread-safe coordination:

:lock: pthread_mutex_t
dongle.mutex: Protects each dongle’s state (in_use, cooldown_until, and wait_queue). Ensures that only one thread modifies or reads the dongle’s internal data at a time.

stop_mutex: Guards the stop_flag global state, allowing safe reads/writes between the monitor and coder threads.

log_mutex: Serializes output to stdout, preventing interleaved or garbled log messages.

:loudspeaker: pthread_cond_t
dongle.cond: Used by coders waiting for a dongle to become available. When a dongle is released, pthread_cond_broadcast wakes all waiters, allowing them to re-evaluate their position in the priority queue.

stop_cond: Used in interruptible_sleep to allow coders to wake early when the simulation stops (burnout or completion). The monitor broadcasts on this condition when stop_flag is set.

:clipboard: Example: Race Condition Prevention
When a coder attempts to acquire a dongle:

The dongle’s mutex is locked.

The coder is inserted into the wait_queue (a thread-safe priority heap).

The coder waits on dongle.cond until it is at the front of the queue, the dongle is free, and the cooldown has elapsed.

The coder removes itself from the queue and marks the dongle as in_use.

The mutex is unlocked.

This ensures that all operations on the dongle are atomic and race-free.

:shield: Thread-Safe Communication
Coders and the monitor communicate via the shared stop_flag, protected by stop_mutex.

The monitor checks for burnout and completion every millisecond. If either condition is met, it sets stop_flag, broadcasts on stop_cond and all dongle.cond to wake sleeping threads.

Coders periodically check stop_flag in their main loop and during sleeps to exit cleanly.

:no_entry_sign: Blocking Cases Handled
:repeat: Deadlock Prevention (Coffman’s Conditions)
To prevent deadlock, Codexion breaks the circular wait condition by enforcing a global resource ordering:

Every coder always acquires the dongle with the lower ID first, then the higher ID.

This eliminates cycles in the resource allocation graph, ensuring that no two coders can block each other indefinitely.

:hourglass_flowing_sand: Starvation Prevention
FIFO scheduler: Ensures fairness by granting dongles in request order.

EDF scheduler: Prioritizes coders with the earliest burnout deadlines, preventing any single coder from being perpetually delayed.

The heap-based wait queue guarantees that the highest-priority waiting coder is always served next.

:ice_cube: Cooldown Handling
Each dongle has a cooldown_until timestamp. After release, the dongle cannot be reacquired until the cooldown period elapses. This is implemented in dongle_wait_turn, where threads wait using pthread_cond_timedwait with a timeout set to the cooldown expiry.

:fire: Precise Burnout Detection
The monitor runs every millisecond and checks each coder’s last_compile_start against the current time. If the difference exceeds time_to_burnout, the monitor:

Sets stop_flag.

Logs the burnout event.

Broadcasts on stop_cond and all dongle.cond to interrupt waiting coders.
This ensures that burnout is detected with millisecond precision.

:scroll: Log Serialization
All log messages are serialized using log_mutex to prevent interleaving. The monitor also suppresses non-burnout logs after stop_flag is set, avoiding noise.

:books: Resources
Classic References
pthreads Tutorial (LLNL)

The Little Book of Semaphores

Coffman’s Deadlock Conditions

EDF Scheduling (Wikipedia)

AI Usage Declaration
This project was developed with the assistance of AI for:

Code review and debugging: Identifying potential race conditions and logic errors in the multithreaded implementation.

Documentation generation: Structuring and refining the README.md, including the synchronization and blocking cases sections.

Conceptual explanations: Clarifying EDF scheduling, deadlock prevention, and pthread primitives.

Code refactoring: Suggesting improvements for memory management (replacing realloc with malloc + free, and proposing fixed-capacity heap allocation).

The core logic, algorithm design, and final code validation were performed by the student.

:busts_in_silhouette: Authors
kpanfero – 42 Student

:page_facing_up: License
This project is part of the 42 curriculum and is provided for educational purposes only.

text

---