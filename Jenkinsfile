pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
    labels:
    app: kaniko
spec:
    containers:
    - name: kaniko
    image: gcr.io/kaniko-project/executor:debug
    command:
    - /busybox/cat
    tty: true
    volumeMounts:
    - name: regcred
        mountPath: /kaniko/.docker
        readOnly: true
    volumes:
    - name: regcred
    secret:
    secretName: regcred


"""
        }
    }
    stages {
        stage('Checkout') {
            steps {
                // В Multibranch Pipeline Jenkins сам клонирует репозиторий,
                // но если нужно, можно явно указать checkout:
                checkout scm
            }
        }
        stage('Build Docker Image with Kaniko') {
            steps {
                container('kaniko') {
                    sh '''
                    /kaniko/executor \
                      --context=`pwd` \
                      --dockerfile=Dockerfile \
                      --destination=aaliyah097/bochat:latest \
                      --verbosity=debug
                    '''
                }
            }
        }
    }
}
