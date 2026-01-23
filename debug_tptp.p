fof(builtin_setminus, axiom, (! [X_SET,A_SET,B_SET] : (in(X_SET,setminus(A_SET,B_SET)) <=> (in(X_SET,A_SET) & ~ (in(X_SET,B_SET)))))).
fof(builtin_cap, axiom, (! [X_SET,A_SET,B_SET] : (in(X_SET,cap(A_SET,B_SET)) <=> (in(X_SET,A_SET) & in(X_SET,B_SET))))).
fof(builtin_cup, axiom, (! [X_SET,A_SET,B_SET] : (in(X_SET,cup(A_SET,B_SET)) <=> (in(X_SET,A_SET) | in(X_SET,B_SET))))).
fof(builtin_empty, axiom, (! [X_SET] : ~ (in(X_SET,empty_set)))).
fof(builtin_singleton, axiom, (! [X_SET,Y_SING] : (in(X_SET,singleton(Y_SING)) <=> X_SET = Y_SING))).
fof(builtin_set_enum, axiom, (! [X_SET,Y_SING,Z_ENUM] : (in(X_SET,set_enum(Y_SING,Z_ENUM)) <=> (X_SET = Y_SING | X_SET = Z_ENUM)))).
fof(builtin_pair_eq, axiom, (! [VA,VB,VC,VD] : (pair(VA,VB) = pair(VC,VD) => (VA = VC & VB = VD)))).
fof(ax_0, axiom, stand_for('$x$ and $y$ agree',X = Y)).
fof(ax_1, axiom, stand_for('$x$ agrees with $y$',X = Y)).
fof(ax_2, axiom, stand_for('$x$ and $y$ are distinct',neq(X,Y))).
fof(ax_3, axiom, (! [X] : stand_for('$x$ belongs to $X$',X))).
fof(ax_4, axiom, (! [X] : stand_for('$X$ contains $x$',X))).
fof(ax_5, axiom, (! [X] : stand_for('$x$ is contained in $X$',X))).
fof(ax_6, axiom, (! [X] : stand_for('$x$ lies in $X$',X))).
fof(ax_7, axiom, (! [X] : stand_for('$x$ is in $X$',X))).
fof(ax_8, axiom, (! [F] : stand_for('the domain of $f$',dom(F)))).
fof(ax_9, axiom, stand_for('$f$ is defined on $X$',dom(F) = X)).
fof(ax_10, axiom, (! [X] : stand_for('the value of $f$ at $x$',f(X)))).
fof(ax_11, axiom, (! [X,Y] : stand_for('$f(x,y)$',f(pair(X,Y))))).
fof(ax_12, axiom, (! [S] : (! [T] : (subclass(T,S) <=> class(T))))).
fof(ax_13, axiom, (! [T] : stand_for('$T \\subseteq S$',T))).
fof(ax_14, axiom, (! [S,T] : ((subclass(S,T) & subclass(T,S)) => S = T))).
fof(ax_15, axiom, (! [S] : (! [X] : (subset(X,S) <=> (set(X) & subset(X,S)))))).
fof(ax_16, axiom, (! [T] : set(T))).
fof(ax_17, axiom, (! [S] : in(S,S))).
fof(ax_18, axiom, (! [F] : (family(F) <=> (set(F) & (! [X_EVERY] : (element(X_EVERY,F) => a_set(X_EVERY))))))).
fof(ax_19, axiom, (! [F] : (disjoint_family(F) <=> (! [X] : (in(X,F) => (! [Y] : (in(Y,F) => (family(F) & disjoint(X,Y))))))))).
fof(ax_20, axiom, (! [X,Y] : (sets(None) => set(times(X,Y))))).
fof(ax_21, axiom, (! [S,T,X,Y] : (objects(None) => ((in(pair(X,Y),times(S,T)) => in(X,S)) & in(Y,T))))).
fof(ax_22, axiom, (! [F] : function(F))).
fof(ax_23, axiom, (! [S,F] : subclass_the_domain(S,F))).
fof(ax_24, axiom, (! [F] : stand_for('$f : S \\rightarrow T$',F))).
fof(ax_25, axiom, (! [X] : (set(X) => set(None)))).
fof(ax_26, axiom, stand_for('$g$ retracts $f$',g(f(X)) = X)).
fof(ax_27, axiom, stand_for('$h$ sections $f$',f(h(Y)) = Y)).
fof(goal_assump_28, axiom, set(x)).
fof(goal, conjecture, set(x)).
