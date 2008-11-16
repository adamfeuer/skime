(begin
	(define fact
	(lambda (n)
		(if (= 0 n)
				1
				(* n (fact (- n 1))))))

(fact 5))