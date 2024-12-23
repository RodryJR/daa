## Introducción
Como un problema NP-Completo, por definición, es un problema que es NP y NP hard, la demostración de que un
problema es NP-Completo consiste en dos partes:
- **Demostrar que es NP**: Dada una instancia del problema, es posible verificar si es una solución es correcta en tiempo polinomial.
- **Demostrar que es NP-Hard**: Dado un problema NP-Hard conocido B, si B es reducible a C, entonces C es NP-Hard.

## Clique de tamaño máximo
#### Reducir Clique de tamaño $k$ a máximo clique:
- La entrada del problema Clique de tamaño $k$ es un grafo no dirigido $G = ( V , E )$
- La entrada al problema de máximo clique es un grafo no dirigido $G' = ( V' , E' )$, donde $V' = V$ y $E' = E$
#### Existe un clique de tamaño $k$ en $G$ <=> existe clique de tamaño máximo $G'$
- **Supongamos que existe un clique de tamaño máximo en $G'$**: Sea $S$ el conjunto de vértices que forman el clique máximo de longitud $q$ en $G'$ . Si $q ≥ k$, entonces al quitar $q − k$ vértices cualesquieras de $S$, como entre todos los vértices restantes existı́an aristas, los vértices restantes forman un clique de tamaño $k$ en $G$. Si $q < k$, entonces no existe un clique de tamaño $k$ en $G$.
- **Supongamos que existe un clique de tamaño $k$ en $G$**: Entonces podemos hallar un clique de tamaño $k$ en $G'$ lo cual pudiera ser este el mayor clique en caso de no haber encontrado ninguno mayor hasta el momento.


Por lo tanto, podemos decir que existe un clique de tamaño k en el grafo G si y solo si existe un clique tamaño máximo. Por ende, cualquier instancia del problema de clique puede reducirse a una instancia del problema de clique de tamaño máximo.