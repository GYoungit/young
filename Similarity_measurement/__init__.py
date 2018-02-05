
def Similarity_word_measurement(stringA, stringB) :

    stringA = stringA.replace(" ", "")
    stringB = stringB.replace(" ", "")

    A_len = len(stringA)
    B_len = len(stringB)

    sum = 0

    for i_index, i in enumerate(stringA) :
        for j_index, j in enumerate(stringB) :
            if i == j :
                word = i
                sum += 1
                stringA = stringA.replace(word, "", 1)
                stringB = stringB.replace(word, "", 1)
                break

    if sum == 0 :
        return 0

    return (float(sum) / float(A_len) + float(sum) / float(B_len)) / 2

def Similarity_list_measurement(listA, listB) :
    listA = [i.replace(" ", "") for i in listA]
    listB = [i.replace(" ", "") for i in listB]

    A_len = len(listA)
    B_len = len(listB)

    sum = 0

    for i_index, i in enumerate(listA) :
        max = 0.0
        for j_index, j in enumerate(listB) :
            sim = Similarity_word_measurement(listA[i_index], listB[j_index])
            if sim > max :
                max = sim

            if len(listB) - 1 == j_index :
                sum += max

    if sum == 0 :
        return 0

    return (float(sum) / float(A_len) + float(sum) / float(B_len)) / 2
