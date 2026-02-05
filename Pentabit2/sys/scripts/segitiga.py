def bikinsegitiga(n):
    for i in range(0, n):
        for j in range(0, n - i):
            print("*", end=' ')
        print("")

bikinsegitiga(5)
