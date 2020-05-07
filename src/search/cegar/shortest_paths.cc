#include "shortest_paths.h"

#include "abstract_search.h"
#include "transition_system.h"
#include "utils.h"

#include "../utils/logging.h"
#include "../utils/memory.h"

#include <cassert>

using namespace std;

namespace cegar {
const Cost ShortestPaths::INF_COSTS = numeric_limits<Cost>::max();
const Cost ShortestPaths::DIRTY = numeric_limits<Cost>::max() - 1;

ShortestPaths::ShortestPaths(const vector<int> &costs, bool debug)
    : debug(debug),
      task_has_zero_costs(any_of(costs.begin(), costs.end(), [](int c) {return c == 0;})) {
    /*
      The code below requires that all operators have positive cost. Negative
      operators are of course tricky, but 0-cost operators are somewhat tricky,
      too. In particular, given perfect g and h values, we want to know which
      operators make progress towards the goal, and this is easy to do if all
      operator costs are positive (then *all* operators that lead to a state
      with the same f value as the current one make progress towards the goal,
      in the sense that following those operators will necessarily take us to
      the goal on a path with strictly decreasing h values), but not if they
      may be 0 (consider the case where all operators cost 0: then the f*
      values of all alive states are 0, so they give us no guidance towards the
      goal).

      If the assumption of no 0-cost operators is violated, the easiest way to
      address this is to replace all 0-cost operators with operators of cost
      epsilon, where epsilon > 0 is small enough that "rounding down" epsilons
      along a shortest path always results in the correct original cost. With
      original integer costs, picking epsilon <= 1/N for a state space with N
      states is sufficient for this. In our actual implementation, we should
      not use floating-point numbers, and if we stick with 32-bit integers for
      path costs, we can run into range issues. The most obvious solution is to
      use 64-bit integers, scaling all original operator costs by 2^32 and
      using epsilon = 1.
    */
    operator_costs.reserve(costs.size());
    for (int cost : costs) {
        operator_costs.push_back(convert_to_64_bit_cost(cost));
    }
}

int ShortestPaths::convert_to_32_bit_cost(Cost cost) const {
    assert(cost != DIRTY);
    if (cost == INF_COSTS) {
        return INF;
    } else if (task_has_zero_costs) {
        return static_cast<int>(cost >> 32);
    } else {
        return cost;
    }
}

Cost ShortestPaths::convert_to_64_bit_cost(int cost) const {
    assert(cost >= 0);
    if (cost == INF) {
        return INF_COSTS;
    } else if (task_has_zero_costs) {
        if (cost == 0) {
            return 1;
        } else {
            return static_cast<uint64_t>(cost) << 32;
        }
    } else {
        return cost;
    }
}

unique_ptr<Solution> ShortestPaths::extract_solution_from_shortest_path_tree(
    int init_id, const Goals &goals) {
    // h* = \infty iff goal is unreachable from this state.
    if (goal_distances[init_id] == INF_COSTS)
        return nullptr;

    int current_state = init_id;
    unique_ptr<Solution> solution = utils::make_unique_ptr<Solution>();
    assert(!goals.count(current_state));
    while (!goals.count(current_state)) {
        assert(utils::in_bounds(current_state, shortest_path));
        const Transition &t = shortest_path[current_state];
        assert(t.op_id != UNDEFINED);
        assert(t.target_id != UNDEFINED);
        assert(t.target_id != current_state);
        assert(goal_distances[t.target_id] <= goal_distances[current_state]);
        solution->push_back(t);
        current_state = t.target_id;
    }
    return solution;
}

void ShortestPaths::mark_dirty(int state) {
    if (debug) {
        cout << "Mark " << state << " as dirty" << endl;
    }
    goal_distances[state] = DIRTY;
    // Previous shortest path is invalid now.
    shortest_path[state] = Transition();
    assert(!count(dirty_states.begin(), dirty_states.end(), state));
    dirty_states.push_back(state);
}

void ShortestPaths::mark_orphaned_predecessors(
    const vector<Transitions> &in, int state) {
    mark_dirty(state);
    for (const Transition &t : in[state]) {
        int prev = t.target_id;
        assert(prev != state);
        assert(prev != UNDEFINED);
        if (goal_distances[prev] != DIRTY &&
            shortest_path[prev].target_id == state) {
            mark_orphaned_predecessors(in, prev);
        }
    }
}

void ShortestPaths::dijkstra_from_orphans(
    const vector<Transitions> &in,
    const vector<Transitions> &out,
    int v, int v1, int v2, bool filter_orphans) {
    /*
      Assumption: all h-values correspond to the perfect heuristic for the
      state space before the split.

      orphans holds the newly computed reverse g-values (i.e., h-values) for
      orphaned states, and SETTLED for settled states. A state is orphaned if
      at least one of its possible shortest-path successors is orphaned,
      starting with s_1. We start by assuming g=\infty for all orphaned states.
    */
    assert(in.size() == out.size());
    int num_states = in.size();
    shortest_path.resize(num_states);
    goal_distances.resize(num_states, 0);
    dirty_states.clear();

    if (debug) {
        cout << "Split " << v << " into " << v1 << " and " << v2 << endl;
        cout << "Goal distances: " << goal_distances << endl;
        cout << "Shortest paths: " << shortest_path << endl;
    }

#ifndef NDEBUG
    Transition old_arc = shortest_path[v];
    bool v1_settled = any_of(out[v1].begin(), out[v1].end(),
                             [&old_arc](const Transition &t) {
                                 return t == old_arc;
                             });
    bool v2_settled = any_of(out[v2].begin(), out[v2].end(),
                             [&old_arc](const Transition &t) {
                                 return t == old_arc;
                             });
    assert(v1_settled ^ v2_settled); // Otherwise, there would be no progress.
    assert(v2_settled); // Implementation detail which we use below.
#endif

    // Copy h value from split state. h(v1) will be updated if necessary.
    goal_distances[v1] = goal_distances[v2] = goal_distances[v];

    /* Due to the way we select splits, the old shortest path from v1 is
       invalid now, but the path from v2 is still valid. We don't explicitly
       invalidate shortest_path[v1] since v and v1 are the same ID. */
    shortest_path[v2] = shortest_path[v];

    /* Update shortest path transitions to split state. The SPT transition to v1
       will be updated again if v1 is dirty. We therefore prefer reconnecting
       states to v2 instead of v1, which is why we test v2 after v1. */
    for (int state : {v1, v2}) {
        for (const Transition &incoming : in[state]) {
            int u = incoming.target_id;
            int op = incoming.op_id;
            Transition &sp = shortest_path[u];
            if (sp.target_id == v &&
                operator_costs[op] == operator_costs[sp.op_id]) {
                sp = Transition(op, state);
            }
        }
    }

    if (debug) {
        cout << "Goal distances: " << goal_distances << endl;
        cout << "Shortest paths: " << shortest_path << endl;
    }

    if (filter_orphans) {
        /*
          Instead of just recursively inserting all orphans, we first push them
          into a candidate queue that is sorted by (old, possibly too low)
          h-values. Then, we try to reconnect them to a non-orphaned state at
          no additional cost. Only if that fails, we flag the candidate as
          orphaned and push its SPT-children (who have strictly larger h-values
          due to no 0-cost operators) into the candidate queue.
        */
        assert(candidate_queue.empty());
        assert(!count(dirty_candidate.begin(), dirty_candidate.end(), true));

        dirty_candidate.resize(num_states, false);
        dirty_candidate[v1] = true;
        candidate_queue.push(goal_distances[v1], v1);

        while (!candidate_queue.empty()) {
            int state = candidate_queue.pop().second;
            if (debug) {
                cout << "Try to reconnect " << state
                     << " with h=" << goal_distances[state] << endl;
            }
            assert(dirty_candidate[state]);
            assert(goal_distances[state] != INF_COSTS);
            assert(goal_distances[state] != DIRTY);
            bool reconnected = false;
            // Try to reconnect to settled, solvable state.
            for (const Transition &t : out[state]) {
                int succ = t.target_id;
                int op_id = t.op_id;
                if (goal_distances[succ] != DIRTY &&
                    goal_distances[succ] != INF_COSTS &&
                    operator_costs[op_id] != INF_COSTS &&
                    goal_distances[succ] + operator_costs[op_id]
                    == goal_distances[state]) {
                    if (debug) {
                        cout << "Reconnect " << state << " to " << succ << " via " << op_id << endl;
                    }
                    shortest_path[state] = Transition(op_id, succ);
                    reconnected = true;
                    break;
                }
            }
            if (!reconnected) {
                mark_dirty(state);
                for (const Transition &t : in[state]) {
                    int prev = t.target_id;
                    if (!dirty_candidate[prev] &&
                        goal_distances[prev] != DIRTY &&
                        shortest_path[prev].target_id == state) {
                        if (debug) {
                            cout << "Add " << prev << " to candidate queue" << endl;
                        }
                        dirty_candidate[prev] = true;
                        candidate_queue.push(goal_distances[prev], prev);
                    }
                }
            }
            dirty_candidate[state] = false;
        }
    } else {
        // v1 and all its predecessors are orphaned.
        mark_orphaned_predecessors(in, v1);
    }

    if (debug) {
        cout << "Goal distances: " << goal_distances << endl;
        cout << "Dirty states: " << dirty_states << endl;
    }

    assert(dirty_states.size() < in.size()); // Goal states must never be dirty.

#ifndef NDEBUG
    for (int i = 0; i < num_states; ++i) {
        if (goal_distances[i] == DIRTY) {
            assert(count(dirty_states.begin(), dirty_states.end(), i) == 1);
        }
    }
#endif

    /*
      Perform a Dijkstra-style exploration to recompute all h values as
      follows. The "initial state" of the search is a virtual state that
      represents all settled states. It is expanded first, starting with a cost
      of 0. Its outgoing arcs are all arcs (in the backward graph) that go from
      a settled state s to a dirty state s' with operator o, and the cost of
      the transition is h(s) + cost(o). (Note that h(s) for settled states is
      known.) After this initialization, proceed with a normal Dijkstra search,
      but only consider arcs that lead from dirty to dirty states.
    */
    int num_orphans = 0;
    open_queue.clear();
    for (int state : dirty_states) {
        Cost &dist = goal_distances[state];
        assert(dist == DIRTY);
        Cost min_dist = INF_COSTS;
        for (const Transition &t : out[state]) {
            int succ = t.target_id;
            int op_id = t.op_id;
            if (goal_distances[succ] != DIRTY) {
                Cost succ_dist = goal_distances[succ];
                Cost cost = operator_costs[op_id];
                assert(cost != INF_COSTS);  // TODO: valid assertion?
                Cost new_dist = (cost != INF_COSTS && succ_dist != INF_COSTS)
                    ? (cost + succ_dist) : INF_COSTS;
                if (new_dist < min_dist) {
                    min_dist = new_dist;
                    shortest_path[state] = Transition(op_id, succ);
                }
            }
        }
        dist = min_dist;
        if (min_dist != INF_COSTS) {
            open_queue.push(dist, state);
            ++num_orphans;
        }
    }
    while (!open_queue.empty()) {
        pair<Cost, int> top_pair = open_queue.pop();
        const Cost g = top_pair.first;
        const int state = top_pair.second;
        assert(goal_distances[state] != DIRTY);
        if (g > goal_distances[state])
            continue;
        assert(g == goal_distances[state]);
        assert(g != INF_COSTS);
        for (const Transition &t : in[state]) {
            int succ = t.target_id;
            int op_id = t.op_id;
            Cost cost = operator_costs[op_id];
            assert(cost != INF_COSTS);
            Cost succ_g = cost + g;

            if (goal_distances[succ] == DIRTY || succ_g < goal_distances[succ]) {
                goal_distances[succ] = succ_g;
                shortest_path[succ] = Transition(op_id, state);
                open_queue.push(succ_g, succ);
            }
        }
    }
}

void ShortestPaths::full_dijkstra(
    const vector<Transitions> &in,
    const unordered_set<int> &goals) {
    open_queue.clear();
    shortest_path.resize(in.size());
    goal_distances = vector<Cost>(in.size(), INF_COSTS);
    for (int goal : goals) {
        Cost dist = 0;
        goal_distances[goal] = dist;
        shortest_path[goal] = Transition();
        open_queue.push(dist, goal);
    }
    while (!open_queue.empty()) {
        pair<Cost, int> top_pair = open_queue.pop();
        Cost old_g = top_pair.first;
        int state_id = top_pair.second;

        Cost g = goal_distances[state_id];
        assert(g < INF_COSTS);
        assert(g <= old_g);
        if (g < old_g)
            continue;
        assert(utils::in_bounds(state_id, in));
        for (const Transition &t : in[state_id]) {
            int succ_id = t.target_id;
            int op_id = t.op_id;
            Cost op_cost = operator_costs[op_id];
            Cost succ_g = (op_cost == INF_COSTS) ? INF_COSTS : g + op_cost;
            if (succ_g < goal_distances[succ_id]) {
                goal_distances[succ_id] = succ_g;
                shortest_path[succ_id] = Transition(op_id, state_id);
                open_queue.push(succ_g, succ_id);
            }
        }
    }
}

bool ShortestPaths::test_distances(
    const vector<Transitions> &in,
    const vector<Transitions> &out,
    const unordered_set<int> &goals) {
    assert(none_of(goal_distances.begin(), goal_distances.end(),
                   [](Cost d) {return d == DIRTY;}));
    int num_states = in.size();

    vector<int> costs;
    costs.reserve(operator_costs.size());
    for (Cost cost : operator_costs) {
        costs.push_back(convert_to_32_bit_cost(cost));
    }

    int init_state = 0;
    vector<int> init_distances = compute_distances(out, costs, {init_state});

    for (int i = 0; i < num_states; ++i) {
        if (debug) {
            cout << "Test state " << i << endl;
        }
        if (goal_distances[i] != INF_COSTS &&
            init_distances[i] != INF &&
            !goals.count(i)) {
            Transition t = shortest_path[i];
            if (debug) {
                cout << "SP: " << t << endl;
            }
            assert(t.is_defined());
            if (debug) {
                cout << "Outgoing transitions: " << out[i] << endl;
            }
            assert(count(out[i].begin(), out[i].end(), t) == 1);
            assert(goal_distances[i] ==
                   operator_costs[t.op_id] + goal_distances[t.target_id]);
        }
    }

    vector<int> goal_distances_32_bit = compute_distances(in, costs, goals);
    vector<int> goal_distances_32_bit_rounded_down;
    goal_distances_32_bit_rounded_down.reserve(goal_distances_32_bit.size());
    for (Cost dist : goal_distances) {
        goal_distances_32_bit_rounded_down.push_back(convert_to_32_bit_cost(dist));
    }

    for (int i = 0; i < num_states; ++i) {
        if (goal_distances_32_bit_rounded_down[i] != goal_distances_32_bit[i] &&
            init_distances[i] != INF) {
            cout << "32-bit INF: " << INF << endl;
            cout << "64-bit 0: " << convert_to_64_bit_cost(0) << endl;
            cout << "64-bit 1: " << convert_to_64_bit_cost(1) << endl;
            cout << "64-bit INF: " << INF_COSTS << endl;
            cout << "64-bit distances: " << goal_distances << endl;
            cout << "32-bit rounded:   " << goal_distances_32_bit_rounded_down << endl;
            cout << "32-bit distances: " << goal_distances_32_bit << endl;
            ABORT("Distances are wrong.");
        }
    }

    return true;
}
}
