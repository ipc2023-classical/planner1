(define (domain grid-visit-all)
(:requirements :typing :action-costs)
    (:types 
        place - object
        order - object
    )
    (:predicates 
        (connected ?x - place ?y - place)
        (at-robot ?x - place)
        (visited ?x - place)
        (last ?o - order)
        (before ?o1 - order ?o2 - order)
        (next-action ?o1 - order ?o2 - order)
        (skippable ?o1 - order)
        (plan-action-move ?o - order ?curpos - place ?nextpos - place)
    )
    (:functions 
    )
    (:action move
        :parameters (?curpos - place ?nextpos - place ?olast - order ?ocurrent - order)
        :precondition (and
                (at-robot ?curpos)
                (connected ?curpos ?nextpos)
                (plan-action-move ?ocurrent ?curpos ?nextpos)
                (next-action ?olast ?ocurrent)
                (last ?olast)
            )
        :effect (and
                (at-robot ?nextpos)
                (not (at-robot ?curpos))
                (visited ?nextpos)
                (last ?ocurrent)
                (not (last ?olast))
                (increase (total-cost) 1)
            )
    )
    (:action skip-original-action-plan
        :parameters (?olast - order ?ocurrent - order)
        :precondition (and
                (next-action ?olast ?ocurrent)
                (last ?olast)
                (skippable ?olast)
            )
        :effect (and
                (last ?ocurrent)
                (not (last ?olast))
                (increase (total-cost) 0)
            )
    )
)
