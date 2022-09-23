from sklearn.model_selection import train_test_split

class DataSet():
    """Generate the input data for ML training and testing."""

    def __init__(self, data, xcol=None, ycol=None, seed=0):
        self.data = data.dropna()
        if xcol is None:
            self.xcol = self.data.columns[:-1]
        else:
            self.xcol = xcol
        if ycol is None:
            self.ycol = self.data.columns[-1]
        else:
            self.ycol = ycol

        ## Train Test Split
        self.train, self.test = train_test_split(self.data, random_state=seed)
        self.xtrain = self.train[self.xcol]
        self.ytrain = self.train[self.ycol]
        self.xtest = self.test[self.xcol]
        self.ytest = self.test[self.ycol]
