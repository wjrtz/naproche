fof(builtin_setminus, axiom, (! [X_SET,A_SET,B_SET] : (in(X_SET,setminus(A_SET,B_SET)) <=> (in(X_SET,A_SET) & ~ (in(X_SET,B_SET)))))).
fof(builtin_cap, axiom, (! [X_SET,A_SET,B_SET] : (in(X_SET,cap(A_SET,B_SET)) <=> (in(X_SET,A_SET) & in(X_SET,B_SET))))).
fof(builtin_cup, axiom, (! [X_SET,A_SET,B_SET] : (in(X_SET,cup(A_SET,B_SET)) <=> (in(X_SET,A_SET) | in(X_SET,B_SET))))).
fof(builtin_empty, axiom, (! [X_SET] : ~ (in(X_SET,empty_set)))).
fof(builtin_singleton, axiom, (! [X_SET,Y_SING] : (in(X_SET,singleton(Y_SING)) <=> X_SET = Y_SING))).
fof(builtin_set_enum, axiom, (! [X_SET,Y_SING,Z_ENUM] : (in(X_SET,set_enum(Y_SING,Z_ENUM)) <=> (X_SET = Y_SING | X_SET = Z_ENUM)))).
fof(builtin_pair_eq, axiom, (! [VA,VB,VC,VD] : (pair(VA,VB) = pair(VC,VD) => (VA = VC & VB = VD)))).
fof(ax_0, axiom, stand_for('$f : X\\to Y$',colon(F,rightarrow(X,Y)))).
fof(ax_1, axiom, (! [B,C] : (sets(None) => equinumerous(B,C)))).
fof(ax_2, axiom, (! [B,C] : (sets(None) => equinumerous(C,B)))).
fof(ax_3, axiom, (! [A,B,C] : (((sets(None) & equinumerous(A,B)) & equinumerous(B,C)) => equinumerous(A,C)))).
fof(ax_4, axiom, (! [X] : (set(X) => ('Dedekind_finite'(X) <=> (! [X_EVERY] : (proper_subset(X_EVERY,X) => ~ (equinumerous(X_EVERY,X)))))))).
fof(ax_5, axiom, (! [X] : (coordinate(X) <=> integer(X)))).
fof(ax_6, axiom, (! [M,N] : square(pair(M,N)))).
fof(ax_7, axiom, (! [X] : (square(X) => (? [M] : (coordinate(M) & (? [N] : (coordinate(N) & X = pair(M,N)))))))).
fof(ax_8, axiom, (! [X_EVERY] : (subset_of_the_checkerboard(X_EVERY) => 'Dedekind_finite'(X_EVERY)))).
fof(ax_9, axiom, mutilated = setminus(checkerboard,corners)).
fof(ax_10, axiom, stand_for('the mutilated checkerboard',mutilated)).
fof(ax_11, axiom, (! [M] : stand_for('$m\\sim n$',M))).
fof(ax_12, axiom, (! [D] : (domino(D) <=> set(D)))).
fof(ax_13, axiom, (! [T] : (domino_tiling(T) <=> disjoint_family(T)))).
fof(ax_14, axiom, (! [X] : (in(X,X) => (! [T] : ('domino_tiling_of_$A$'(T) <=> domino_tiling(T)))))).
fof(ax_15, axiom, (! [X] : stand_for('$x$ is white',X))).
fof(ax_16, axiom, (! [X,Y] : ((adjacent(X,Y) => black(X)) <=> white(Y)))).
fof(ax_17, axiom, black(pair('\'0\'','\'0\''))).
fof(ax_18, axiom, black(pair('\'7\'','\'7\''))).
fof(ax_19, axiom, (! [X_GEN] : (in(X_GEN,black) <=> (in(X_GEN,checkerboard) & black(X_GEN))))).
fof(ax_20, axiom, (! [X_GEN] : (in(X_GEN,white) <=> (in(X_GEN,checkerboard) & white(X_GEN))))).
fof(ax_21, axiom, set(black)).
fof(ax_22, axiom, set(white)).
fof(ax_23, axiom, (! [X] : (in(X,checkerboard) => adjacent('Swap'(X),X)))).
fof(ax_24, axiom, (! [X] : (in(X,checkerboard) => 'Swap'('Swap'(X)) = X))).
fof(ax_25, axiom, (! [X] : (in(X,checkerboard) => (black(X) <=> white('Swap'(X)))))).
fof(ax_26, axiom, equinumerous(black,white)).
fof(ax_27, axiom, (! [A,T,X] : (in(X,A) => in('Sw'(T,A,X),A)))).
fof(ax_28, axiom, (! [A,T,X] : (in(X,A) => 'Sw'(T,A,'Sw'(T,A,X)) = X))).
fof(ax_29, axiom, (! [A,T,X] : (in(X,A) => black('Sw'(T,A,X))))).
fof(ax_30, axiom, (! [A,T,X] : (in(X,A) => white('Sw'(T,A,X))))).
fof(ax_31, axiom, (! [A] : equinumerous(cap(A,black),cap(A,white)))).
fof(ax_32, axiom, cap(mutilated,white) = white).
fof(ax_33, axiom, proper_subset(cap(mutilated,black),black)).
fof(step_0, axiom, domino_tiling(T,mutilated)).
fof(step_1, axiom, equinumerous(cap(mutilated,black),cap(mutilated,white))).
fof(step_2, axiom, equinumerous(cap(mutilated,black),white)).
fof(step_3, axiom, equinumerous(cap(mutilated,black),black)).
fof(goal, conjecture, false).