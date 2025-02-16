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
                image: gcr.io/kaniko-project/executor:latest
                command:
                - cat
                tty: true
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
