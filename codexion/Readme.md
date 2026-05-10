*This project has been created as part of the 42 curriculum by <yourlogin>*

# Codexion

## Description

**Codexion** is a multithreaded simulation of a circular co‑working hub where coders share USB dongles to compile quantum code.  
Each coder cycles through three phases — **compile** (requires two adjacent dongles), **debug**, and **refactor** — and must complete a minimum number of compilations before burning out.  

The program models the shared dongle pool as a set of mutex‑protected resources and uses custom priority queues to arbitrate access under two scheduling policies: **First‑In‑First‑Out (FIFO)** and **Earliest Deadline First (EDF)**.  
A dedicated monitor thread detects burnouts (when a coder’s deadline expires) with high precision and stops the simulation.  

The goal is to practise thread synchronisation, deadlock avoidance, scheduling algorithms, and real‑time monitoring, all within the constraints of the 42 coding norm.

## Instructions

### Compilation
```bash
make
The executable codexion is produced.
The Makefile uses cc with the flags -Wall -Wextra -Werror -pthread and supports the standard rules: all, clean, fclean, re.

Execution
bash
./codexion number_of_coders time_to_burnout time_to_compile time_to_debug \
           time_to_refactor number_of_compiles_required dongle_cooldown scheduler
Arguments (all mandatory):

Argument	Description	Constraints
number_of_coders	Number of coders (and dongles)	≥ 1
time_to_burnout	Maximum time (ms) without compiling before burnout	≥ 1
time_to_compile	Duration (ms) of a compile phase	≥ 1
time_to_debug	Duration (ms) of a debug phase	≥ 1
time_to_refactor	Duration (ms) of a refactor phase	≥ 1
number_of_compiles_required	How many compilations each coder must finish before stopping	≥ 0
dongle_cooldown	Cooldown time (ms) after a dongle is released	≥ 0
scheduler	Arbitration policy for dongle allocation	fifo or edf
Behaviour
The simulation ends when every coder has compiled at least number_of_compiles_required times, or a coder burns out.

All state changes are written to standard output, one line per event:

timestamp X has taken a dongle

timestamp X is compiling

timestamp X is debugging

timestamp X is refactoring

timestamp X burned out

Logs are serialised – no interleaving of characters from multiple threads.

The program cleans up all heap‑allocated memory before exiting (no leaks).

Blocking Cases Handled
Deadlock Prevention
Circular‑wait is broken by a strict acquisition order: each coder always takes its lower‑indexed dongle first. This prevents the hold‑and‑wait cycle and eliminates deadlocks.
Coffman condition addressed: circular wait is impossible.

Starvation Prevention
FIFO: a global request counter guarantees that requests are served in the exact order they arrive – no coder can be overtaken.

EDF: the coder with the smallest last_compile_start + time_to_burnout is chosen. A tie‑breaker (lower coder ID) ensures deterministic arbitration and prevents indefinite postponement.

Cooldown Handling
Each dongle stores a cooldown_end timestamp (in milliseconds). After a coder releases the dongle, the monitor thread will not assign it to a waiting coder until the current time reaches cooldown_end.
This guarantees that the physical cooldown period is respected exactly.

Precise Burnout Detection
A separate monitor thread loops frequently (every 500 µs) and compares each coder’s last_compile_start with the current time.

The moment current_time - last_compile_start >= time_to_burnout, the coder is flagged burned_out, a log message is printed, and the simulation is stopped.

The design ensures the burnout message appears no later than 10 ms after the actual deadline, fulfilling the real‑time requirement.

Log Serialisation
All output is protected by a dedicated log mutex. Any thread that calls printf must first lock this mutex, guaranteeing that two messages never appear on the same line.

Thread Synchronisation Mechanisms
Primitive	Purpose
pthread_mutex_t	Protects all shared data: dongle state, coder statistics, simulation running/stop flags, the global request counter, and the log output mutex. Every read or write of shared memory happens inside a critical section protected by the appropriate mutex.
pthread_cond_t	Allows a coder to sleep while waiting for a dongle. The condition variable is associated with the dongle’s mutex. When the monitor thread makes a dongle available, it calls pthread_cond_broadcast to wake all waiting coders; each then re‑checks the condition and either proceeds or goes back to sleep.
Custom priority queue (min‑heap)	Embedded in each dongle, stores pending requests ordered by FIFO request number or EDF deadline. All operations on the queue are performed while holding the dongle’s mutex, making it inherently thread‑safe.
Coordination Examples
Acquiring a dongle
text
coder thread:
  lock(dongle.mutex)
  push request into dongle.wait (priority queue)
  while (dongle.held_by != my_id && sim.running)
      pthread_cond_wait(&dongle.cond, &dongle.mutex)   // releases mutex, waits
  if (!sim.running) -> remove request, unlock, return error
  check coder.burned_out under coder.mutex
  if burned_out -> release dongle, return error
  unlock(dongle.mutex)
  return success

monitor thread:
  lock(dongle.mutex)
  if (dongle.held_by == 0 && now >= dongle.cooldown_end && !pq_empty(dongle.wait))
      pop highest‑priority request
      dongle.held_by = popped.coder_id
      dongle.cooldown_end = 0
      pthread_cond_broadcast(&dongle.cond)
  unlock(dongle.mutex)
Preventing race on burnout detection
The monitor locks coder.mutex before reading last_compile_start and writing burned_out.

The coder thread locks the same mutex when checking its own burned_out flag after acquiring a dongle.
This guarantees that a burnout decision and a simultaneous “start compiling” are not observed in an inconsistent state.

Stopping the simulation
sim_stop() locks the global state mutex, sets running = 0, unlocks, and then broadcasts on every dongle’s condition variable.
All waiting coders wake, see that sim_running(sim) returns false, remove themselves from the queue, release any held dongle, and exit their thread.

Resources
Classic References
The Little Book of Semaphores – Allen B. Downey: patterns for concurrency control and deadlock analysis.

Dining Philosophers problem – the classical synchronisation problem that inspired this project.

POSIX Threads Programming – Blaise Barney, Lawrence Livermore National Laboratory: a comprehensive guide to pthread.

Operating System Concepts – Silberschatz, Galvin, Gagne: chapters on process/thread synchronisation, scheduling algorithms (FIFO, EDF), and deadlock conditions.

AI Usage
Initial scaffolding – AI generated the base structure (header file, main loop, empty stubs) to speed up the initial layout.

Priority queue – AI provided a min‑heap implementation that was adapted for the t_req struct and integrated into the dongle waiting mechanism.

Deadlock avoidance – AI suggested the consistent lower‑index‑first resource ordering to break circular wait.

Debugging & correctness – AI helped detect race conditions (e.g., unprotected compile counter, unsafe pointer hack) and proposed fixes.
All AI‑generated fragments were carefully reviewed, merged into the overall design, and rewritten where necessary to comply with the 42 Norm.