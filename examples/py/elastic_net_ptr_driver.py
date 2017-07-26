import h2ogpuml as h2ogpuml
from h2ogpuml.types import *

'''
Elastic Net

   minimize    (1/2) ||Ax - b||_2^2 + \alpha * \lambda ||x||_1 + 0.5 * (1-\alpha) * \lambda ||x||_2

   for 100 values of \lambda, and alpha in [0,1]
   See <h2ogpuml>/matlab/examples/lasso_path.m for detailed description.
'''


def elastic_net(X, y, nGPUs = 0, nlambda = 100, nfolds = 5, nalpha = 5, validFraction = 0.2):
    solver = h2ogpuml.GLM

    sharedA = 0
    sourceDev = 0
    nThreads = None
    intercept = 1
    standardize = 0
    lambda_min_ratio = 1e-9
    nFolds = nfolds
    nLambdas = nlambda
    nAlphas = nalpha

    if standardize:
        print("implement standardization transformer")
        exit()

    # Setup Train/validation Set Split
    morig = X.shape[0]
    norig = X.shape[1]
    print("Original m=%d n=%d" % (morig, norig))
    fortran = X.flags.f_contiguous
    print("fortran=%d" % fortran)

    # Do train/valid split
    HO = int(validFraction * morig)
    H = morig - HO
    print("Size of Train rows=%d valid rows=%d" % (H, HO))
    trainX = np.copy(X[0:H, :])
    trainY = np.copy(y[0:H])
    validX = np.copy(X[H:-1, :])
    validY = np.copy(y[H:-1])
    trainW = np.copy(trainY) * 0.0 + 1.0  # constant unity weight

    mTrain = trainX.shape[0]
    mvalid = validX.shape[0]
    print("mTrain=%d mvalid=%d" % (mTrain, mvalid))

    if intercept == 1:
        trainX = np.hstack([trainX, np.ones((trainX.shape[0], 1), dtype=trainX.dtype)])
        validX = np.hstack([validX, np.ones((validX.shape[0], 1), dtype=validX.dtype)])
        n = trainX.shape[1]
        print("New n=%d" % n)

    ## Constructor
    print("Setting up solver")
    enet = solver(sharedA, nThreads, nGPUs, 'c' if fortran else 'r', intercept, standardize, lambda_min_ratio, nLambdas,
                  nFolds, nAlphas)

    ## First, get backend pointers
    print("Uploading")
    print(trainX.dtype)
    print(trainY.dtype)
    print(validX.dtype)
    print(validY.dtype)
    print(trainW.dtype)
    a, b, c, d, e = enet.upload_data(sourceDev, trainX, trainY, validX, validY, trainW)

    ## Solve
    print("Solving")
    # below 0 ignored if trainX gives precision
    givefullpath = 0
    precision = 0  # float
    if givefullpath == 1:
        Xvsalphalambda, Xvsalpha = enet.fitptr(sourceDev, mTrain, n, mvalid, precision, a, b, c, d, e, givefullpath)
    else:
        Xvsalpha = enet.fitptr(sourceDev, mTrain, n, mvalid, precision, a, b, c, d, e, givefullpath)
    print("Done Solving")

    # show something about Xvsalphalambda and Xvsalpha

    print("Predicting")
    if givefullpath == 1:
        validPredsvsalphalambdapure, validPredsvsalphapure = enet.predictptr(sourceDev, mTrain, n, mvalid, precision, c,
                                                                             givefullpath)
    else:
        validPredsvsalphapure = enet.predictptr(sourceDev, mTrain, n, mvalid, precision, c, givefullpath)

    print("Done Predicting")

    # show something about validPredsvsalphalambdapure, validPredsvsalphapure

    return enet


if __name__ == "__main__":
    import numpy as np
    #from numpy.random import randn
    #  m=1000
    #  n=100
    #  A=randn(m,n)
    #  x_true=(randn(n)/n)*float64(randn(n)<0.8)
    #  b=A.dot(x_true)+0.5*randn(m)
    #import pandas as pd
    import feather

    df = feather.read_dataframe("../../../h2oai-prototypes/glm-bench/ipums.feather")
    # df = pd.read_csv("../cpp/ipums.txt", sep=" ", header=None)
    print(df.shape)
    X = np.array(df.iloc[:, :df.shape[1] - 1], dtype='float32', order='C')
    y = np.array(df.iloc[:, df.shape[1] - 1], dtype='float32', order='C')
    # elastic_net(X, y, nGPUs=2, nlambda=100, nfolds=5, nalpha=5, validFraction=0.2)
    elastic_net(X, y, nGPUs=2, nlambda=100, nfolds=2, nalpha=1, validFraction=0.2)
