1. Single coder (always burns out)
bash
./codexion 1 1000 200 300 400 2 50 fifo
Expected output (approx):

text
1000 1 burned out
What it tests:

With one coder, only one dongle exists, but compiling requires two dongles.

Coder never acquires both dongles → never starts compiling → burnout after time_to_burnout ms.

Validates that the monitor correctly detects and logs burnout within 10 ms precision.

Also checks that no deadlock or hang occurs with a single thread.


2. Successful completion (no burnout)
bash
./codexion 3 3000 200 100 100 2 10 fifo
Expected outcome: All three coders compile twice, simulation ends normally (no “burned out” message).

What it tests:

time_to_burnout (2000 ms) is large enough to allow each coder to complete its cycle (compile+debug+refactor) and wait for dongles.

All coders reach compiles_required = 2 and simulation stops cleanly.

Validates that the monitor correctly detects when all coders have finished and terminates without printing burnout.

3. Burnout due to insufficient time to complete
bash
./codexion 3 500 200 300 400 3 50 fifo
Expected outcome: Some coder burns out because time_to_burnout (500 ms) is shorter than the time needed to complete a full cycle (compile+debug+refactor = 200+300+400 = 900 ms) plus dongle waiting time.

What it tests:

Burnout detection: monitor checks deadlines every 1 ms and prints burnout within 10 ms.

After burnout, all threads stop and the program exits (no further logs).

The log contains a single burned out line for the first coder that misses its deadline.

4. EDF scheduler – deadline-based priority
bash
./codexion 4 1000 200 200 200 5 30 edf
Expected outcome: Coders with earliest deadlines (based on last_compile_start + time_to_burnout) are prioritised when acquiring dongles, preventing starvation.

What it tests:

EDF scheduling logic: dongles grant to the coder with the smallest deadline value (deterministic tie-breaker by smaller coder ID).

Cooldown (30 ms) is respected.

Liveness: no coder is starved indefinitely under feasible parameters.

Custom priority queue implementation correctly orders nodes by EDF comparison.

5. FIFO scheduler – first‑come, first‑served
bash
./codexion 3 1500 100 100 100 4 20 fifo
Expected outcome: Coders acquire dongles in the order they requested them (by timestamp). The dongle wait queue is a FIFO priority queue (key = request time).

What it tests:

FIFO arbitration: dongle granted to the coder whose request arrived earliest.

The custom heap comparison uses compare_fifo (lower request time first).

Cooldown (20 ms) ensures dongles are not reacquired instantly.

6. Cooldown effect – dongle unavailable after release
bash
./codexion 2 800 150 150 150 2 200 fifo
Expected outcome: After a coder releases a dongle, it becomes unavailable for 200 ms. Other coders must wait until cooldown expires. This may cause delays and could lead to burnout if parameters are tight.

What it tests:

dongle_cooldown is enforced: cooldown_until timestamp is set on release, and dongle_acquire checks get_current_ms() >= d->cooldown_until.

With cooldown longer than compile+debug+refactor time, coders will block and possibly burn out. Check logs for correct cooldown timing.

7. Large number of coders – stress test
bash
./codexion 10 2000 100 100 100 3 10 fifo
Expected outcome: All ten coders complete three compiles each without burnout. The simulation runs correctly with many threads competing for dongles.

What it tests:

No race conditions, deadlocks, or memory leaks with high concurrency.

Thread creation and joining scale properly.

Logs are serialised (no interleaved lines) due to log_mutex.

No segmentation faults or undefined behaviour.

8. Invalid argument rejection
bash
# Too few arguments
./codexion 3 1000 200 300 400 2 50

# Negative number
./codexion -2 1000 200 300 400 2 50 fifo

# Non‑integer
./codexion abc 1000 200 300 400 2 50 fifo

# Invalid scheduler
./codexion 3 1000 200 300 400 2 50 roundrobin
Expected outcome: Program prints usage error and exits with non‑zero status. No simulation starts.

What it tests:

Input validation as required: check argc == 9, all numbers are positive integers, scheduler string is exactly "fifo" or "edf".

Graceful failure without crashing.

9. Pre‑emptive burnout detection (tight deadline)
bash
./codexion 2 300 100 150 100 1 10 fifo
Expected outcome: Coder 1 may start compiling, but due to cooldown (10 ms) and scheduling, one coder’s deadline (300 ms) may be missed because the other holds dongles too long. Burnout occurs.

What it tests:

Monitor thread checks every 1 ms and logs burnout within 10 ms of the exact millisecond when now - last_compile_start >= time_to_burnout.

Precision requirement: burnout log timestamp difference ≤ 10 ms from actual deadline miss.

10. Minimal compiles required (zero or one)
bash
./codexion 2 1000 200 200 200 1 50 fifo
Expected outcome: Each coder compiles once, then simulation stops immediately (no burnout).

What it tests:

number_of_compiles_required = 1 – simulation ends as soon as all coders have compiled at least once.

No unnecessary extra cycles.

(Note: 0 is invalid and should be rejected by argument parser.)

time_to_burnout ≥ (N - 1) × (time_to_compile + dongle_cooldown)
                  + time_to_compile
                  + time_to_debug
                  + time_to_refactor
                  + 1          (small safety margin)

short
time_to_burnout ≥ 2 × time_to_compile + time_to_debug + time_to_refactor + dongle_cooldown + 1

Easy
1. Safe formula to guarantee no burnout
For a given set of parameters, compute a safe time_to_burnout:

text
safe_burnout = (N - 1) * (time_to_compile + dongle_cooldown)
               + time_to_compile
               + time_to_debug
               + time_to_refactor
               + 10          (small safety margin)
This ensures that the worst‑case waiting time for a coder to get both dongles again is shorter than the deadline.

2. Test scenarios (all should complete without burnout)
Run these commands; they must never print "burned out".

a) Small number of coders
bash
./codexion 4 5000 200 100 100 3 60 fifo
Safe value: (4-1)*(200+60) + 200+100+100 = 3*260 + 400 = 1180 → 5000 is far larger → safe.

b) Medium number of coders
bash
./codexion 50 20000 300 150 150 2 80 fifo
Safe value: 49*(300+80) + 300+150+150 = 49*380 + 600 = 18620 + 600 = 19220 → 20000 is safe.

c) Upper bound of N (200 coders)
bash
./codexion 200 100000 500 200 200 2 100 fifo
Safe value: 199*(500+100) + 500+200+200 = 199*600 + 900 = 119400 + 900 = 120300 → 100000 is a bit low; adjust to e.g. 130000:

bash
./codexion 200 130000 500 200 200 2 100 fifo
d) EDF scheduler with safe parameters
bash
./codexion 10 8000 150 100 100 4 60 edf
Safe value: 9*(150+60) + 150+100+100 = 9*210 + 350 = 1890 + 350 = 2240 → 8000 is safe.

3. Edge cases that must produce burnout (to test correct behaviour)
Single coder (impossible to get two dongles):

bash
./codexion 1 1000 200 100 100 2 50 fifo
Expected: 1000 1 burned out (or within 10 ms).

Overloaded system (small time_to_burnout):

bash
./codexion 10 1000 200 100 100 2 60 fifo
Safe value would be 9*260 + 400 = 2740 → 1000 is too small → at least one coder burns out.

Cooldown large enough to cause starvation:

bash
./codexion 3 500 100 50 50 2 400 fifo
Cooldown 400 ms, compile 100 ms → dongles locked for 500 ms (including compile) → deadlines likely missed.

Test 1: No burnout – safe parameters (baseline)
Command:

bash
./codexion 4 5000 200 100 100 3 60 fifo
safe_burnout (formula) = (4-1)*(200+60) + 200+100+100 = 3*260 + 400 = 1180 → 5000 > 1180 ✅

Expected:

No "burned out" line in the output.

All 4 coders print "is compiling" exactly 3 times each.

Last line is some "is refactoring" or "is debugging" (simulation stops after all required compiles).

Verification:

bash
./codexion 4 5000 200 100 100 3 60 fifo | grep -c "burned out"   # must be 0
./codexion 4 5000 200 100 100 3 60 fifo | grep "is compiling" | wc -l  # must be 12 (4 coders * 3 compiles)
Test 2: Burnout – single coder (impossible to compile)
Command:

bash
./codexion 1 1000 200 100 100 2 60 fifo
Expected:

Only one line: 1000 1 burned out (timestamp may be exactly 1000 or within ±10 ms).

No "has taken a dongle" or "is compiling".

Timing tolerance check:
The difference between simulation start (0) and burnout timestamp must be between 1000 and 1010 ms. (Because gettimeofday and usleep have small inaccuracies.)

Verification script snippet:

bash
output=$(./codexion 1 1000 200 100 100 2 60 fifo)
time=$(echo "$output" | grep "burned out" | cut -d' ' -f1)
if [ $time -ge 1000 ] && [ $time -le 1010 ]; then echo "PASS"; else echo "FAIL (time=$time)"; fi
Test 3: Burnout – overloaded system (deadline too short)
Command:

bash
./codexion 10 1200 200 100 100 2 60 fifo
Safe value would be 9*(200+60) + 200+100+100 = 9*260 + 400 = 2740 → 1200 is too small → expected burnout.

Expected:

At least one "burned out" line (the first coder that misses its deadline).

Simulation stops after that; no further compiles for that coder.

Check timing:
For the burned‑out coder, the difference between its last "is compiling" timestamp and the "burned out" timestamp must be ≥ time_to_burnout and ≤ time_to_burnout + 10.

Example: If coder X compiled last at time T, burnout at B, then B - T should be between 1200 and 1210 ms.

Test 4: No dongle duplication – check overlapping compile intervals for adjacent coders
Because dongles are arranged in a ring, adjacent coders share a dongle and therefore cannot compile at the same time. This is a strong invariant.

Command (any safe run with ≥ 2 coders):

bash
./codexion 5 10000 300 150 150 2 80 fifo > log.txt
Check using a script:
Extract each coder’s compile intervals (start and end timestamps). For any two coders that are neighbours (id i and i+1, plus wrap‑around between N and 1), their compile intervals must not overlap.

Example neighbour pairs: (1,2), (2,3), (3,4), (4,5), (5,1).

Quick manual check from log.txt:
For each pair, scan for lines like:

text
<start> X is compiling
...
<end_approx = start + time_to_compile> (not directly logged, but we know duration)
But easier: two adjacent coders cannot both have "is compiling" lines where their intervals intersect. Because the shared dongle is held by one of them during compilation plus cooldown.

A simple heuristic: if you see two adjacent coders both compiling at times that overlap (i.e., their start timestamps are less than time_to_compile apart), that would indicate a conflict. But this is not 100% precise. For full correctness, you would need to simulate the dongle assignment, but that’s complex.

Alternative: Trust that your mutex‑protected dongle acquisition prevents duplication. The spec requires that you protect each dongle’s state with a mutex, which your code does. So no two coders can hold the same dongle simultaneously. This test is more about verifying the implementation – you can do a code review.

Test 5: State correctness – coder phases follow required order
For each coder, the sequence of actions must be:

text
has taken a dongle
has taken a dongle
is compiling
is debugging
is refactoring
(and then repeat from the top)
Check command:

bash
./codexion 3 5000 200 100 100 2 60 fifo | grep "1 " | awk '{print $3}' > coder1_actions.txt
Expected pattern (for coder 1):

text
has
has
is
is
is
has
has
is
is
is
You can write a small script to validate that for each coder, the sequence alternates correctly and no action is missing.

Test 6: Log serialisation – no interleaved lines
Command:

bash
./codexion 10 10000 200 100 100 2 60 fifo > log.txt
Check: Each line must start with a timestamp and contain exactly one action. Use:

bash
grep -v "^[0-9]\+ [0-9]\+ \(has taken a dongle\|is compiling\|is debugging\|is refactoring\|burned out\)$" log.txt
If this produces any output, the format is broken.

Also ensure that two messages never appear on the same line. The log mutex prevents this.

Test 7: EDF scheduler – burnout with feasible parameters? (edge)
EDF should be able to schedule a set of tasks if total utilisation ≤ 1. But because dongles are a shared resource, even EDF can cause burnout if the system is overloaded.

Safe EDF test (no burnout):

bash
./codexion 6 8000 150 100 100 3 70 edf
Check no burnout.

Overloaded EDF (burnout):

bash
./codexion 6 1500 150 100 100 3 70 edf
Expected: burnout because deadlines are too tight.

Verification: Same as FIFO cases – look for "burned out" line.

Test 8: Cooldown enforcement – dongle not reused before cooldown expires
This is tricky to test from logs because we don’t see which dongle is taken. However, we can infer: after a coder releases dongles (i.e., after "is compiling" ends), the same dongle cannot be taken by another coder until dongle_cooldown ms have passed.

We can test by looking at two consecutive compiles on the same coder: the time between its "is compiling" end and the start of its next "is compiling" must be at least time_to_debug + time_to_refactor + (possibly waiting time). That doesn’t directly check cooldown.

Better approach: Use a short cooldown and high contention. For example:

bash
./codexion 3 10000 100 50 50 2 200 fifo
Cooldown = 200 ms. After a compile ends (at T+100), the dongles are locked until T+300. If another coder tries to acquire a dongle that was just released, it will have to wait. You can observe in the log that the next "has taken a dongle" for that dongle (by any coder) cannot happen before T+300. Without dongle IDs, this is hard to verify automatically. Manual inspection with small N can help.

1. Cooldown behaviour
Goal: Ensure a dongle cannot be taken again within dongle_cooldown ms after being released.

Test 1A – Two coders, long cooldown, observe waiting
bash
./codexion 2 2000 200 100 100 2 500 fifo
dongle_cooldown = 500 ms (long).

Coder 1 compiles first (takes both dongles). After release, both dongles are locked for 500 ms.

Coder 2 must wait until cooldown expires.

Expected log pattern:

Coder 1: 0 compile start, 200 debug start, 300 refactor start, 400 refactor end → tries to acquire again at ~400.

Coder 2: It will try to acquire dongles during this time. Because of cooldown, its has taken a dongle lines will appear after the cooldown ends (i.e., after 200 + 500 = 700 ms for the first dongle, and similarly for the second). The first has taken for coder 2 should not happen before ~700.

Verification:
Extract timestamps of the first two has taken lines for coder 2. Their difference from the end of coder 1’s compile (200) must be ≥ 500 ms (within a small tolerance).

Test 1B – Same coder cannot re‑acquire the same dongle immediately
bash
./codexion 1 5000 200 100 100 2 300 fifo
Single coder: only one dongle exists. It cannot compile because it needs two, but it can still attempt to take dongles.

The log will show it tries to take the same dongle repeatedly after cooldown? Actually with one coder and one dongle, dongle_acquire will succeed (if available) but then it will wait forever for the second dongle. This tests cooldown on that single dongle: after release, it must be unavailable for 300 ms. You can observe the gap between consecutive has taken a dongle lines for the same coder (it will keep trying). The gap should be ≥ 300 ms.

Verification:
Count the time between two successive has taken lines for coder 1. They must differ by ≥ 300 ms.

2. Scheduler differences: FIFO vs EDF
Goal: Show that EDF can avoid starvation while FIFO may cause burnout under the same load.

Test 2A – FIFO leads to starvation (burnout)
bash
./codexion 3 2500 500 300 200 2 50 fifo
time_to_burnout = 2500. All three coders have the same initial deadline (sim start). FIFO serves them in order of request.

With contention, the third coder may be delayed enough to miss its deadline.

Expected: At least one coder burns out.

Test 2B – EDF avoids burnout (same parameters)
bash
./codexion 3 2500 500 300 200 2 50 edf
EDF prioritises the coder with the earliest deadline. Initially all deadlines are equal; tie‑breaker by coder ID (smaller first). But after the first cycle, deadlines diverge. EDF should give fairer access.

Expected: No burnout (all three complete required compiles).

Verification: Compare the two runs – FIFO shows a burned out line, EDF does not.

3. Refactoring timing
Goal: Verify that after finishing refactoring, the coder immediately attempts to acquire dongles and compile again (no unnecessary delays).

Test 3 – Track a single coder’s timeline
bash
./codexion 2 5000 200 100 100 2 60 fifo
Focus on coder 1. Extract its logs:

bash
./codexion 2 5000 200 100 100 2 60 fifo | grep " 1 " > coder1.txt
The sequence should be:

is compiling (first compile)

is debugging

is refactoring

Then immediately after the refactor finish timestamp, the next action should be has taken a dongle (or possibly already taken dongles before refactor ended? No, because dongles are released after compile, and refactoring does not hold dongles). So the time gap between the refactor start and the next has taken should be exactly time_to_refactor (100 ms) plus minimal scheduling overhead.

Verification:
Take the timestamp of is refactoring (call it T_ref_start). The next has taken a dongle should occur at or after T_ref_start + time_to_refactor. The difference must be ≥ 100 ms (and not much larger; a few ms due to scheduling is okay).

4. Log serialisation (no interleaved lines)
Goal: Ensure that messages from different threads never appear on the same line, and each line is complete.

Test 4 – High concurrency stress
bash
./codexion 100 50000 200 100 100 3 60 fifo > stress.log
Run with many coders (max 200) to maximise interleaving opportunities.

Check that every line matches the exact format and no two messages are merged.

Verification script:

bash
# Check each line matches pattern
grep -vE "^[0-9]+ [0-9]+ (has taken a dongle|is compiling|is debugging|is refactoring|burned out)$" stress.log > badlines
if [ -s badlines ]; then
    echo "Log serialisation FAILED:"
    cat badlines
else
    echo "Log serialisation PASS"
fi
Also check that the log is not empty and that the last line is either a burned out or a refactoring line (normal termination).

We need to modify the EDF tie-breaker to prefer the higher coder ID when deadlines are equal. The current compare_edf function (used in the heap) prioritises the smaller coder ID as a tie-breaker. We'll change it to prioritise the larger coder ID.

Modified compare_edf function
In codexion.c, replace the existing compare_edf with:

c
int compare_edf(t_heap_node a, t_heap_node b)
{
    if (a.key != b.key)
        return a.key < b.key;          // earlier deadline = higher priority
    // Tie‑breaker: higher coder_id gets priority
    return a.coder_id > b.coder_id;
}
The heap is a min‑heap based on the comparator: if cmp(a, b) returns 1, a has higher priority and will be placed above b.
For equal deadlines, we want the coder with larger ID to be popped first – hence a.coder_id > b.coder_id.

Validation test: equal deadlines contention
We will create a scenario where two coders have the same deadline and compete for the same dongle. The test will verify that the coder with the higher ID wins (i.e., takes the dongle first).

Test design
Use 2 coders (IDs 1 and 2) – they share one dongle (the one between them).

Set time_to_burnout very large so nobody burns out prematurely.

Force both coders to have identical last_compile_start so their EDF deadlines are equal.
The simplest way: start the simulation, let both try to compile for the first time. Initially both have last_compile_start = sim_start_ms, hence same deadline (sim_start_ms + time_to_burnout).
They will both request the same dongle (the one they share). With EDF and the new tie-breaker, coder 2 (higher ID) should acquire the dongle first.

But note: each coder needs two dongles (left and right). For two coders:

Coder 1 has left dongle 2? Wait, with 2 coders: dongle 1 is between coder 1 and coder 2? Actually the spec: dongle i is between coder i and coder i+1 (with wrap). For 2 coders:

Dongle 1 between coder 1 and coder 2.

Dongle 2 between coder 2 and coder 1 (wrap). So both dongles are shared between the two coders.
Thus both coders need both dongles. They will compete for dongle 1 and dongle 2 simultaneously. The tie-breaker will affect which coder gets each dongle first.

To isolate the tie-breaker, we can force them to request one specific dongle at the same time. Because the acquisition order is: first acquire left dongle (or right depending on ID order – we always acquire in increasing dongle ID order to avoid deadlock). So both will first request dongle 1 (since dongle 1 < dongle 2). The tie-breaker decides who gets dongle 1. With higher ID preferred, coder 2 should get dongle 1 first.

Concrete test command
Use a small time_to_compile to quickly see the result. Also use a large time_to_burnout to avoid early termination.

bash
./codexion 2 10000 100 100 100 2 10 edf
We then examine the logs: the first has taken a dongle line for dongle 1 (the first dongle taken by any coder) should belong to coder 2.

Automated verification script
bash
#!/bin/bash
make clean && make

echo "=== EDF tie‑breaker test (higher ID preferred) ==="
log=$(./codexion 2 10000 100 100 100 2 10 edf)
# Find the very first "has taken a dongle" line (the first dongle taken)
first_taker=$(echo "$log" | grep "has taken a dongle" | head -1 | awk '{print $2}')
if [ "$first_taker" = "2" ]; then
    echo "PASS: coder 2 (higher ID) got the first dongle"
else
    echo "FAIL: first dongle taken by coder $first_taker (expected 2)"
fi
Expected output
text
PASS: coder 2 (higher ID) got the first dongle
If the tie-breaker were still the smaller ID, coder 1 would take the dongle first and the test would fail.

Additional verification: equal deadlines with more coders
For a more thorough test, use 3 coders. Coder 3 has the highest ID. In the initial state all deadlines equal. Coder 3 should be the first to acquire any dongle when competing with coder 1 and coder 2.

bash
./codexion 3 10000 100 100 100 2 10 edf | grep "has taken a dongle" | head -1 | awk '{print $2}'
Expected output: 3.

Final note
The change is minimal and only affects the tie-breaking rule. The rest of the scheduler logic (heap implementation, deadline computation) remains unchanged. This modification ensures that the EDF policy is deterministic and now favours higher‑numbered coders when deadlines are exactly equal, as requested.