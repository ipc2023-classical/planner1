#include "cartesian_abstraction_generator.h"

#include "explicit_abstraction.h"
#include "types.h"

#include "../option_parser.h"
#include "../plugin.h"

#include "../cegar/abstraction.h"
#include "../cegar/abstract_state.h"
#include "../cegar/subtask_generators.h"
#include "../utils/logging.h"
#include "../utils/rng_options.h"

#include <memory>

using namespace std;

namespace cost_saturation {
CartesianAbstractionGenerator::CartesianAbstractionGenerator(
    const options::Options &opts)
    : subtask_generators(
          opts.get_list<shared_ptr<cegar::SubtaskGenerator>>("subtasks")),
      max_transitions(opts.get<int>("max_transitions")),
      rng(utils::parse_rng_from_options(opts)),
      num_transitions(0) {
}

static unique_ptr<Abstraction> convert_abstraction(
    const cegar::Abstraction &cartesian_abstraction) {
    int num_states = cartesian_abstraction.get_num_states();
    vector<vector<Successor>> backward_graph(num_states);

    // Store non-looping transitions.
    for (cegar::AbstractState *state : cartesian_abstraction.get_states()) {
        // Ignore transitions from dead-end or unreachable states.
        if (state->get_h_value() == INF ||
            state->get_search_info().get_g_value() == INF) {
            continue;
        }
        int src = state->get_node()->get_state_id();
        for (const cegar::Transition &transition : state->get_outgoing_transitions()) {
            // Ignore transitions from dead-end states (we know target is reachable).
            if (transition.target->get_h_value() == INF) {
                continue;
            }
            int target = transition.target->get_node()->get_state_id();
            backward_graph[target].emplace_back(transition.op_id, src);
        }
    }
    for (vector<Successor> &succesors : backward_graph) {
        succesors.shrink_to_fit();
    }

    // Store self-loop info.
    vector<int> looping_operators = cartesian_abstraction.get_looping_operators();

    // Store goals.
    vector<int> goal_states;
    goal_states.reserve(cartesian_abstraction.get_goals().size());
    for (const cegar::AbstractState *goal : cartesian_abstraction.get_goals()) {
        goal_states.push_back(goal->get_node()->get_state_id());
    }

    shared_ptr<cegar::RefinementHierarchy> refinement_hierarchy =
        cartesian_abstraction.get_refinement_hierarchy();
    AbstractionFunction state_map =
        [refinement_hierarchy](const State &state) {
            assert(refinement_hierarchy);
            return refinement_hierarchy->get_local_state_id(state);
        };

    return utils::make_unique_ptr<ExplicitAbstraction>(
        state_map,
        move(backward_graph),
        move(looping_operators),
        move(goal_states));
}

void CartesianAbstractionGenerator::build_abstractions_for_subtasks(
    const vector<shared_ptr<AbstractTask>> &subtasks,
    function<bool()> total_size_limit_reached,
    Abstractions &abstractions) {
    int remaining_subtasks = subtasks.size();
    for (shared_ptr<AbstractTask> subtask : subtasks) {
        // TODO: Allow specifying this on the commandline.
        const int max_states = INF;
        /* To make the abstraction refinement process deterministic, we don't
           set a time limit. */
        const double max_time = numeric_limits<double>::infinity();
        // Has no effect since we compute the cost partitioning(s) later.
        const bool use_general_costs = true;

        cegar::Abstraction cartesian_abstraction(
            subtask,
            max_states,
            max(1, (max_transitions - num_transitions) / remaining_subtasks),
            max_time,
            use_general_costs,
            cegar::PickSplit::MAX_REFINED,
            *rng);

        num_transitions += cartesian_abstraction.get_num_non_looping_transitions();

        int init_h = cartesian_abstraction.get_h_value_of_initial_state();

        abstractions.push_back(convert_abstraction(cartesian_abstraction));

        if (total_size_limit_reached() || init_h == INF) {
            break;
        }

        --remaining_subtasks;
    }

}

Abstractions CartesianAbstractionGenerator::generate_abstractions(
    const shared_ptr<AbstractTask> &task) {
    utils::Timer timer;
    utils::Log log;
    log << "Build Cartesian abstractions" << endl;

    function<bool()> total_size_limit_reached =
        [&] () {
            return num_transitions >= max_transitions;
        };

    Abstractions abstractions;
    for (shared_ptr<cegar::SubtaskGenerator> subtask_generator : subtask_generators) {
        cegar::SharedTasks subtasks = subtask_generator->get_subtasks(task);
        build_abstractions_for_subtasks(subtasks, total_size_limit_reached, abstractions);
        if (total_size_limit_reached()) {
            break;
        }
    }

    log << "Cartesian abstractions built: " << abstractions.size() << endl;
    log << "Time for building Cartesian abstractions: " << timer << endl;
    return abstractions;
}

static shared_ptr<AbstractionGenerator> _parse(OptionParser &parser) {
    parser.document_synopsis(
        "Cartesian abstraction generator",
        "");

    parser.add_list_option<shared_ptr<cegar::SubtaskGenerator>>(
        "subtasks",
        "subtask generators",
        "[landmarks(order=random, random_seed=0),goals(order=random, random_seed=0)]");
    parser.add_option<int>(
        "max_transitions",
        "maximum sum of real transitions (excluding self-loops) over "
        " all abstractions",
        "1000000",
        Bounds("0", "infinity"));
    parser.add_option<bool>(
        "debug",
        "print debugging info",
        "false");
    utils::add_rng_options(parser);

    Options opts = parser.parse();
    if (parser.dry_run())
        return nullptr;

    return make_shared<CartesianAbstractionGenerator>(opts);
}

static PluginShared<AbstractionGenerator> _plugin("cartesian", _parse);
}
